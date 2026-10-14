-- Vendas para envio à GfK.
-- Placeholders substituídos pelo script (formato dd/mm/aaaa):
--   {data_inicio} -> inclusivo
--   {data_fim}    -> exclusivo (o script passa o dia seguinte ao fim do período)
--
-- ATENÇÃO: o script pagina o resultado acrescentando "OFFSET ... FETCH NEXT ..." ao final.
-- Por isso a query deve TERMINAR com um ORDER BY determinístico (último critério
-- = chave única: ITE.NUNOTA, ITE.SEQUENCIA), senão linhas podem repetir ou sumir entre páginas.
SELECT
  CAB.DTNEG AS [DATA]
  ,CAB.CODEMP AS [LOJA]
  ,'PA' AS [UF]
  ,'BELÉM' AS [CIDADE]
  ,GRU.DESCRGRUPOPROD AS [CATEGORIA]
  ,ITE.CODPROD AS [COD_INTERNO]
  ,PRO.MARCA AS [MARCA/FABRICANTE]
  ,PRO.AD_MODELOREF AS [MODELO]
  ,PRO.DESCRPROD AS [DESCRICAO COMPLETA DO PRODUTO]
  ,ITE.QTDNEG AS [QTDE]
  ,ITE.VLRUNIT AS [PREÇO UNITÁRIO]
  ,ITE.VLRTOT AS [FATURAMENTO TOTAL]

FROM
  TGFCAB CAB, TGFITE ITE, TGFPRO PRO, TGFGRU GRU

WHERE
  CAB.NUNOTA = ITE.NUNOTA AND ITE.CODPROD = PRO.CODPROD AND PRO.CODGRUPOPROD = GRU.CODGRUPOPROD
  AND CAB.CODTIPOPER IN (1112,1101,1105,1181,1110)
  AND DTNEG >= '{data_inicio}'
  AND DTNEG  < '{data_fim}'

ORDER BY CAB.DTNEG, CAB.CODEMP, ITE.CODPROD, ITE.NUNOTA, ITE.SEQUENCIA
