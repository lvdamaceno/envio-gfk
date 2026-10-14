"""Geração da planilha Excel a partir do resultado da consulta."""

import re
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

# O DbExplorer devolve datas como texto no formato "ddMMyyyy HH:mm:ss"
_DATA_SANKHYA = re.compile(r"^\d{8} \d{2}:\d{2}:\d{2}$")


def _converter(valor):
    if isinstance(valor, str) and _DATA_SANKHYA.match(valor):
        return datetime.strptime(valor, "%d%m%Y %H:%M:%S")
    return valor


def gerar_xlsx(colunas: list[str], linhas: list[list], destino: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Vendas"

    ws.append(colunas)
    for celula in ws[1]:
        celula.font = Font(bold=True)

    for linha in linhas:
        ws.append([_converter(v) for v in linha])

    # Datas exibidas como dd/mm/aaaa. Os códigos devem ser minúsculos (padrão OOXML):
    # em maiúsculas o Excel aceita, mas Numbers/LibreOffice mostram "DD/10/YYYY".
    for linha in ws.iter_rows(min_row=2):
        for celula in linha:
            if isinstance(celula.value, datetime):
                celula.number_format = "dd/mm/yyyy"

    destino.parent.mkdir(parents=True, exist_ok=True)
    wb.save(destino)
    return destino
