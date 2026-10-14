"""Ponto de entrada: consulta o Sankhya, gera o .xlsx e envia para o FTP.

Por padrão o período é a última semana completa (segunda a domingo).

Uso:
    python main.py --sem-ftp              # só consulta e gera o arquivo (teste)
    python main.py                        # fluxo completo
    python main.py --inicio 05/10/2026 --fim 11/10/2026   # período manual (ambos inclusivos)
    python main.py --testar-telegram      # só envia uma mensagem de teste
"""

import argparse
import logging
import sys
from datetime import date, datetime, timedelta

from envio_gfk import config, ftp, planilha, sankhya, telegram
from envio_gfk.config import RAIZ

ARQUIVO_SQL = RAIZ / "sql" / "vendas_gfk.sql"
PASTA_SAIDA = RAIZ / "saida"

log = logging.getLogger("envio_gfk")


def semana_anterior(hoje: date) -> tuple[date, date]:
    """Última semana completa (segunda a domingo) antes da semana de `hoje`.

    Ex.: em qualquer dia de 12/10/2026 (seg) a 18/10/2026 (dom) -> 05/10/2026 a 11/10/2026.
    """
    segunda_atual = hoje - timedelta(days=hoje.weekday())  # weekday(): segunda = 0
    inicio = segunda_atual - timedelta(days=7)
    return inicio, inicio + timedelta(days=6)


def _data(valor: str) -> date:
    """Converte dd/mm/aaaa para o argparse."""
    return datetime.strptime(valor, "%d/%m/%Y").date()


def _args():
    p = argparse.ArgumentParser(description="Exporta vendas do Sankhya e envia para o FTP da GfK.")
    p.add_argument("--inicio", type=_data, help="dd/mm/aaaa (inclusivo); padrão: segunda da semana passada")
    p.add_argument("--fim", type=_data, help="dd/mm/aaaa (inclusivo); padrão: domingo da semana passada")
    p.add_argument("--sem-ftp", action="store_true", help="apenas gera o arquivo, sem enviar ao FTP")
    p.add_argument("--testar-telegram", action="store_true", help="só envia uma notificação de teste")
    args = p.parse_args()
    if (args.inicio is None) != (args.fim is None):
        p.error("informe --inicio e --fim juntos (ou nenhum dos dois)")
    if args.inicio is None:
        args.inicio, args.fim = semana_anterior(date.today())
    if args.fim < args.inicio:
        p.error("--fim não pode ser anterior a --inicio")
    return args


def executar(inicio: date, fim: date, enviar_ftp: bool) -> None:
    """Executa o fluxo para o período de `inicio` a `fim` (ambos inclusivos)."""
    # A query usa fim exclusivo (DTNEG < data_fim) para pegar o último dia inteiro
    sql = ARQUIVO_SQL.read_text(encoding="utf-8").format(
        data_inicio=_br(inicio), data_fim=_br(fim + timedelta(days=1))
    )
    periodo = f"{_br(inicio)} a {_br(fim)}"

    cfg_sankhya = config.sankhya()
    log.info("Autenticando no Sankhya (%s)...", cfg_sankhya.base_url)
    token = sankhya.autenticar(cfg_sankhya)

    log.info("Executando consulta do período %s...", periodo)
    colunas, linhas = sankhya.executar_query(cfg_sankhya, token, sql)
    log.info("%d linha(s) retornada(s).", len(linhas))

    _limpar_saida()
    nome = f"vendas_gfk_{inicio:%Y%m%d}_{fim:%Y%m%d}.xlsx"
    arquivo = planilha.gerar_xlsx(colunas, linhas, PASTA_SAIDA / nome)
    log.info("Arquivo gerado: %s", arquivo)

    if not enviar_ftp:
        log.info("--sem-ftp informado: envio ao FTP ignorado (arquivo mantido para conferência).")
        return

    cfg_ftp = config.ftp()
    log.info("Enviando para ftp://%s%s ...", cfg_ftp.host, cfg_ftp.diretorio)
    ftp.enviar(cfg_ftp, arquivo)
    log.info("Envio concluído.")
    arquivo.unlink()
    log.info("Arquivo local removido: %s", arquivo.name)
    telegram.notificar(
        f"Período: {periodo}\nArquivo: {nome}\nLinhas: {len(linhas)}",
        sucesso=True,
    )


def _limpar_saida() -> None:
    """Remove planilhas de execuções anteriores para a pasta não acumular arquivos."""
    for antigo in PASTA_SAIDA.glob("*.xlsx"):
        antigo.unlink()
        log.info("Arquivo antigo removido: %s", antigo.name)


def _br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _args()
    if args.testar_telegram:
        telegram.notificar("Mensagem de teste: a notificação está configurada.", sucesso=True)
        return 0
    try:
        executar(args.inicio, args.fim, enviar_ftp=not args.sem_ftp)
        return 0
    except Exception as erro:
        log.exception("Falha na execução")
        if not args.sem_ftp:
            periodo = f"{_br(args.inicio)} a {_br(args.fim)}"
            telegram.notificar(f"Período: {periodo}\nErro: {erro}", sucesso=False)
        return 1


if __name__ == "__main__":
    sys.exit(main())
