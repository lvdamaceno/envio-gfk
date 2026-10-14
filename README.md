# envio-gfk

Script que consulta as vendas no **Sankhya** pela API oficial, gera uma planilha Excel (`.xlsx`) e envia o arquivo para o **FTP da GfK**.

```
Sankhya (OAuth 2.0) ──► DbExplorerSP.executeQuery ──► .xlsx em saida/ ──► FTP ──► Telegram
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
│   └── telegram.py       # notificação de sucesso/falha
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

## Notificação no Telegram

Ao final do fluxo completo, o script envia uma mensagem de **sucesso** (período, arquivo e nº de linhas) ou de **falha** (período e erro).
É opcional: sem `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` no `.env`, a mensagem só vai para o log.
Uma falha do Telegram nunca interrompe o envio, apenas gera um erro no log.

Configuração:

1. No Telegram, abra o **@BotFather**, envie `/newbot` e siga as instruções. Copie o token (ex.: `123456789:AAH...`) para `TELEGRAM_BOT_TOKEN`.
2. Descubra o `TELEGRAM_CHAT_ID`:
   - **Conversa direta:** envie qualquer mensagem ao seu bot.
   - **Grupo:** adicione o bot ao grupo e envie uma mensagem mencionando o bot (ex.: `/start@NomeDoBot`).
   - Depois acesse `https://api.telegram.org/bot<TOKEN>/getUpdates` no navegador e copie o valor de `"chat":{"id": ...}`. IDs de grupo são negativos (ex.: `-1001234567890`).
3. Teste: `python main.py --testar-telegram`

## Uso

```bash
# Testar apenas a consulta + geração do arquivo (não envia ao FTP)
python main.py --sem-ftp

# Fluxo completo (consulta, gera e envia ao FTP)
python main.py

# Período manual (reenvio/correção) — início e fim inclusivos, formato dd/mm/aaaa
python main.py --inicio 05/10/2026 --fim 11/10/2026

# Apenas enviar uma notificação de teste ao Telegram
python main.py --testar-telegram
```

O arquivo é salvo em `saida/vendas_gfk_<inicio>_<fim>.xlsx` (ex.: `vendas_gfk_20261005_20261011.xlsx`).

Para a pasta `saida/` não acumular arquivos:
- antes de gerar a nova planilha, todos os `.xlsx` existentes em `saida/` são excluídos;
- após o envio ao FTP com sucesso, o arquivo gerado também é excluído;
- com `--sem-ftp`, ou se o envio falhar, o arquivo é mantido para conferência (e será removido na próxima execução).

O script retorna código de saída `0` em sucesso e `1` em falha (útil para cron/agendadores).

### Período

Sem `--inicio`/`--fim`, o período é sempre a **última semana completa, de segunda a domingo**, anterior à semana em que o script roda (função `semana_anterior` em `main.py`):

| Execução                  | Período enviado              |
|---------------------------|------------------------------|
| seg 12/10/2026 (normal)   | 05/10/2026 a 11/10/2026      |
| qua 14/10/2026 (atrasada) | 05/10/2026 a 11/10/2026      |
| seg 19/10/2026            | 12/10/2026 a 18/10/2026      |

Ou seja, rodar no meio da semana nunca envia a semana corrente (incompleta).

`--inicio` e `--fim` devem ser informados juntos e são **inclusivos**. Na query, `{data_fim}` recebe o dia seguinte ao fim (`DTNEG < data_fim`), para incluir o último dia inteiro.

A execução é agendada externamente (cron) toda **segunda às 09:00**. O cálculo usa a data local do servidor; ajuste o fuso do servidor/cron para `America/Belem` (ou equivalente) se ele estiver em UTC.

## Detalhes técnicos

- **Autenticação:** `POST {SANKHYA_BASE_URL}/authenticate` com header `X-Token` e corpo form-urlencoded. O `access_token` expira em ~5 min, então é gerado a cada execução.
- **Consulta:** `POST {SANKHYA_BASE_URL}/gateway/v1/mge/service.sbr?serviceName=DbExplorerSP.executeQuery&outputType=json` com `Authorization: Bearer <token>`. A resposta traz `fieldsMetadata` (colunas) e `rows` (linhas). `status` diferente de `"1"` é tratado como erro.
- **Datas:** o Sankhya devolve datas como texto `ddMMyyyy HH:mm:ss`; o script converte para data real no Excel (formato `dd/mm/aaaa`).
- **Limite de 5.000 linhas e paginação:** o `DbExplorerSP.executeQuery` retorna no máximo 5.000 linhas por chamada (testado em 14/10/2026; não consta na documentação oficial) e, ao truncar, **não** dá erro: mantém `status: "1"` e sinaliza só `burstLimit: true`. Por isso o script:
  - **pagina** a consulta acrescentando `OFFSET n ROWS FETCH NEXT 4000 ROWS ONLY` ao final do SQL (`TAMANHO_PAGINA` em `envio_gfk/sankhya.py`) e junta as páginas até vir uma incompleta;
  - exige que a query **termine com um `ORDER BY` determinístico** — o último critério deve ser a chave única (`ITE.NUNOTA, ITE.SEQUENCIA`), senão linhas podem repetir ou sumir entre páginas. **Mantenha isso ao editar `sql/vendas_gfk.sql`**;
  - ainda assim trata `burstLimit: true` como **falha**, por segurança.
  - Validado com 18.547 linhas (5 páginas): sem duplicatas e total igual ao `COUNT(*)`.
- **Notificações:** com `--sem-ftp` (modo de teste) nada é enviado ao Telegram.
- **FTP:** usa `ftplib` da biblioteca padrão. Com `FTP_TLS=true` usa FTPS explícito (canal de dados também criptografado).
  - O FTP da GfK (`gimftp.gfk.com`) **exige FTPS**: com `FTP_TLS=false` o login falha com `503 ... AUTH SSL/TLS required`.
  - O servidor da GfK encerra o canal de dados sem o fechamento TLS, o que gera `Connection reset by peer` ao final do envio mesmo com o arquivo completo. O script registra um aviso e **confere o tamanho do arquivo no FTP**; só considera sucesso se for igual ao local.

## TODO

- [x] Notificação via Telegram de sucesso/falha (`envio_gfk/telegram.py`).
- [x] Calcular o período automaticamente a cada execução (última semana seg–dom).
- [ ] Agendar a execução semanal (seg 09:00) no servidor de hospedagem.
- [x] Paginar a consulta (limite de 5.000 linhas por chamada do Sankhya).
- [ ] Confirmar com a GfK o formato aceito (`.xlsx` vs `.xls` legado) e o padrão de nome do arquivo.
