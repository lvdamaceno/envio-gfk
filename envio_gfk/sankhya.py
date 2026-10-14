"""Cliente mínimo da API oficial do Sankhya (OAuth 2.0 + API Gateway).

Docs: https://developer.sankhya.com.br/reference/guia-integracao
"""

import requests

from .config import SankhyaConfig

TIMEOUT = 120  # segundos


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


def executar_query(cfg: SankhyaConfig, token: str, sql: str) -> tuple[list[str], list[list]]:
    """Executa um SELECT via serviço DbExplorerSP.executeQuery.

    Retorna (nomes_das_colunas, linhas).
    """
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
            "do DbExplorerSP.executeQuery). É preciso paginar a consulta ou reduzir o período."
        )
    colunas = [campo["name"] for campo in resultado["fieldsMetadata"]]
    return colunas, resultado.get("rows", [])
