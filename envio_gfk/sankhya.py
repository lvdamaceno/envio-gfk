"""Cliente mínimo da API oficial do Sankhya (OAuth 2.0 + API Gateway).

Docs: https://developer.sankhya.com.br/reference/guia-integracao
"""

import logging

import requests

from .config import SankhyaConfig

TIMEOUT = 120  # segundos
# O DbExplorerSP.executeQuery devolve no máximo 5.000 linhas por chamada;
# usamos páginas menores por margem de segurança.
TAMANHO_PAGINA = 4000

log = logging.getLogger(__name__)


class SankhyaErro(Exception):
    pass


def autenticar(cfg: SankhyaConfig) -> str:
    """Obtém o access_token (Bearer) via client_credentials. O token expira em ~5 min."""
    resp = requests.post(
        f"{cfg.base_url}/authenticate",
        headers={"X-Token": cfg.x_token},
        data={
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
            "grant_type": "client_credentials",
        },
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        raise SankhyaErro(f"Falha na autenticação ({resp.status_code}): {resp.text[:500]}")
    return resp.json()["access_token"]


def _executar(cfg: SankhyaConfig, token: str, sql: str) -> dict:
    """Uma chamada ao DbExplorerSP.executeQuery; retorna o responseBody."""
    resp = requests.post(
        f"{cfg.base_url}/gateway/v1/mge/service.sbr",
        params={"serviceName": "DbExplorerSP.executeQuery", "outputType": "json"},
        headers={"Authorization": f"Bearer {token}"},
        json={"serviceName": "DbExplorerSP.executeQuery", "requestBody": {"sql": sql}},
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        raise SankhyaErro(f"Erro HTTP {resp.status_code} na consulta: {resp.text[:500]}")

    corpo = resp.json()
    # status "1" = sucesso; qualquer outro valor traz o motivo em statusMessage
    if str(corpo.get("status")) != "1":
        raise SankhyaErro(f"Sankhya retornou erro: {corpo.get('statusMessage') or corpo}")

    resultado = corpo["responseBody"]
    # O DbExplorer corta o resultado em 5.000 linhas SEM erro (status continua "1"),
    # sinalizando apenas burstLimit=true. Melhor falhar do que enviar dados incompletos.
    if resultado.get("burstLimit"):
        raise SankhyaErro(
            f"Resultado truncado pelo Sankhya (limite de {len(resultado.get('rows', []))} linhas "
            "do DbExplorerSP.executeQuery). Reduza TAMANHO_PAGINA em envio_gfk/sankhya.py."
        )
    return resultado


def executar_query(
    cfg: SankhyaConfig, token: str, sql: str, tamanho_pagina: int = TAMANHO_PAGINA
) -> tuple[list[str], list[list]]:
    """Executa um SELECT paginado (OFFSET/FETCH do SQL Server), juntando todas as páginas.

    O SQL deve terminar com um ORDER BY determinístico. Retorna (nomes_das_colunas, linhas).
    """
    base = sql.strip().rstrip(";")
    if "ORDER BY" not in base.upper():
        raise ValueError("A query precisa terminar com ORDER BY para ser paginada.")

    linhas: list[list] = []
    pagina = 1
    while True:
        sql_pagina = f"{base}\nOFFSET {len(linhas)} ROWS FETCH NEXT {tamanho_pagina} ROWS ONLY"
        resultado = _executar(cfg, token, sql_pagina)
        novas = resultado.get("rows", [])
        linhas.extend(novas)
        log.info("Página %d: %d linha(s) (total %d).", pagina, len(novas), len(linhas))
        if len(novas) < tamanho_pagina:  # página incompleta = última
            break
        pagina += 1

    colunas = [campo["name"] for campo in resultado["fieldsMetadata"]]
    return colunas, linhas
