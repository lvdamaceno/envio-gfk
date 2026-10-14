"""Notificação via Telegram.

TODO: implementar o envio real usando a Bot API:
  POST https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/sendMessage
  body: {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}
  - adicionar TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no config.py e .env.example
  - nunca deixar uma falha na notificação derrubar o script (só logar)
"""

import logging

log = logging.getLogger(__name__)


def notificar(mensagem: str, sucesso: bool) -> None:
    log.info("[telegram - TODO] %s %s", "✅" if sucesso else "❌", mensagem)
