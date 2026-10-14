"""Ponto de entrada: consulta o Sankhya, gera o .xlsx e envia para o FTP.

Uso:
    python main.py --sem-ftp              # só consulta e gera o arquivo (teste)
    python main.py                        # fluxo completo
    python main.py --inicio 05/10/2026 --fim 11/10/2026
"""

import argparse
import logging
import sys
from datetime import datetime

from envio_gfk import config, ftp, planilha, sankhya, telegram
from envio_gfk.config import RAIZ

# TODO: datas fixas para teste; depois serão calculadas a cada execução
DATA_INICIO_PADRAO = "05/10/2026"  # inclusivo
DATA_FIM_PADRAO = "11/10/2026"  # exclusivo

ARQUIVO_SQL = RAIZ / "sql" / "vendas_gfk.sql"
PASTA_SAIDA = RAIZ / "saida"

log = logging.getLogger("envio_gfk")


def _data(valor: str) -> str:
    """Valida dd/mm/aaaa para o argparse."""
    datetime.strptime(valor, "%d/%m/%Y")
    return valor


def _args():
    p = argparse.ArgumentParser(description="Exporta vendas do Sankhya e envia para o FTP da GfK.")
    p.add_argument("--inicio", type=_data, default=DATA_INICIO_PADRAO, help="dd/mm/aaaa (inclusivo)")
    p.add_argument("--fim", type=_data, default=DATA_FIM_PADRAO, help="dd/mm/aaaa (exclusivo)")
    p.add_argument("--sem-ftp", action="store_true", help="apenas gera o arquivo, sem enviar ao FTP")
    return p.parse_args()


def executar(inicio: str, fim: str, enviar_ftp: bool) -> None:
    sql = ARQUIVO_SQL.read_text(encoding="utf-8").format(data_inicio=inicio, data_fim=fim)

    cfg_sankhya = config.sankhya()
    log.info("Autenticando no Sankhya (%s)...", cfg_sankhya.base_url)
    token = sankhya.autenticar(cfg_sankhya)

    log.info("Executando consulta de %s até %s (exclusivo)...", inicio, fim)
    colunas, linhas = sankhya.executar_query(cfg_sankhya, token, sql)
    log.info("%d linha(s) retornada(s).", len(linhas))

    nome = f"vendas_gfk_{_compacta(inicio)}_{_compacta(fim)}.xlsx"
    arquivo = planilha.gerar_xlsx(colunas, linhas, PASTA_SAIDA / nome)
    log.info("Arquivo gerado: %s", arquivo)

    if not enviar_ftp:
        log.info("--sem-ftp informado: envio ao FTP ignorado.")
        return

    cfg_ftp = config.ftp()
    log.info("Enviando para ftp://%s%s ...", cfg_ftp.host, cfg_ftp.diretorio)
    ftp.enviar(cfg_ftp, arquivo)
    log.info("Envio concluído.")
    telegram.notificar(f"Arquivo {nome} enviado ao FTP ({len(linhas)} linhas).", sucesso=True)


def _compacta(data: str) -> str:
    """05/10/2026 -> 20261005"""
    return datetime.strptime(data, "%d/%m/%Y").strftime("%Y%m%d")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _args()
    try:
        executar(args.inicio, args.fim, enviar_ftp=not args.sem_ftp)
        return 0
    except Exception as erro:
        log.exception("Falha na execução")
        if not args.sem_ftp:
            telegram.notificar(f"Falha no envio GfK: {erro}", sucesso=False)
        return 1


if __name__ == "__main__":
    sys.exit(main())
