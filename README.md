# envio-gfk

Script que consulta as vendas no **Sankhya** pela API oficial, gera uma planilha Excel (`.xlsx`) e envia o arquivo para o **FTP da GfK**.

```
Sankhya (OAuth 2.0) ──► DbExplorerSP.executeQuery ──► .xlsx em saida/ ──► FTP ──► Telegram (TODO)
```

## Estrutura

```
envio-gfk/
├── main.py               # ponto de entrada (orquestra o fluxo e os argumentos)
├── sql/vendas_gfk.sql    # a query; edite aqui para mudar colunas/filtros
├── envio_gfk/
│   ├── config.py         # lê as variáveis do .env
│   ├── sankhya.py        # autenticação + execução da query na API
│   ├── planilha.py       # gera o .xlsx
│   ├── ftp.py            # upload para o FTP/FTPS
│   └── telegram.py       # notificação (TODO, hoje só loga)
├── saida/                # arquivos gerados (ignorados pelo git)
├── .env.example          # modelo de configuração
├── .gitignore            # ignora .env, .venv, saida/ etc.
└── requirements.txt
```

## Instalação

Requer Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate          # fish: source .venv/bin/activate.fish
pip install -r requirements.txt
cp .env.example .env               # e preencha as credenciais
```

## Credenciais do Sankhya

A API usa OAuth 2.0 (`client_credentials`). São necessários três valores ([guia oficial](https://developer.sankhya.com.br/reference/guia-integracao)):

| Variável                | Onde obter                                                        |
|-------------------------|-------------------------------------------------------------------|
| `SANKHYA_CLIENT_ID`     | Área do Desenvolvedor → Solução → componente de integração         |
| `SANKHYA_CLIENT_SECRET` | Idem                                                              |
| `SANKHYA_X_TOKEN`       | Sankhya Om → **Configurações Gateway** → Cadastrar aplicação      |

> Token de sandbox só funciona com Client ID/Secret de sandbox, e o de produção só com os de produção. Erro **401** quase sempre é essa mistura.
> Para sandbox, use `SANKHYA_BASE_URL=https://api.sandbox.sankhya.com.br`.

O usuário vinculado à aplicação precisa ter acesso ao **Explorador de Banco de Dados** (serviço `DbExplorerSP.executeQuery`) e às tabelas `TGFCAB`, `TGFITE`, `TGFPRO` e `TGFGRU`.

## Uso

```bash
# Testar apenas a consulta + geração do arquivo (não envia ao FTP)
python main.py --sem-ftp

# Fluxo completo (consulta, gera e envia ao FTP)
python main.py

# Outro período (início inclusivo, fim exclusivo, formato dd/mm/aaaa)
python main.py --inicio 05/10/2026 --fim 11/10/2026
```

O arquivo é salvo em `saida/vendas_gfk_<inicio>_<fim>.xlsx` (ex.: `vendas_gfk_20261005_20261011.xlsx`).
O script retorna código de saída `0` em sucesso e `1` em falha (útil para cron/agendadores).

### Período

Por enquanto as datas padrão estão **fixas** em `main.py` (`DATA_INICIO_PADRAO` / `DATA_FIM_PADRAO`) para testes.
A query usa os placeholders `{data_inicio}` e `{data_fim}`, substituídos pelo script.

## Detalhes técnicos

- **Autenticação:** `POST {SANKHYA_BASE_URL}/authenticate` com header `X-Token` e corpo form-urlencoded. O `access_token` expira em ~5 min, então é gerado a cada execução.
- **Consulta:** `POST {SANKHYA_BASE_URL}/gateway/v1/mge/service.sbr?serviceName=DbExplorerSP.executeQuery&outputType=json` com `Authorization: Bearer <token>`. A resposta traz `fieldsMetadata` (colunas) e `rows` (linhas). `status` diferente de `"1"` é tratado como erro.
- **Datas:** o Sankhya devolve datas como texto `ddMMyyyy HH:mm:ss`; o script converte para data real no Excel (formato `dd/mm/aaaa`).
- **Volume:** o log mostra a quantidade de linhas retornadas. O DbExplorer pode limitar o número de linhas por consulta; se o total parecer “redondo” ou menor que o esperado, confira no Sankhya Om.
- **FTP:** usa `ftplib` da biblioteca padrão. Com `FTP_TLS=true` usa FTPS explícito (canal de dados também criptografado).

## TODO

- [ ] Notificação via Telegram de sucesso/falha (`envio_gfk/telegram.py`).
- [ ] Calcular o período automaticamente a cada execução (substituir as datas fixas).
- [ ] Agendar a execução (cron/launchd).
- [ ] Confirmar com a GfK o formato aceito (`.xlsx` vs `.xls` legado) e o padrão de nome do arquivo.
