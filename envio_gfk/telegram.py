"""Notificação via Telegram (Bot API).

Se TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID não estiverem configurados, apenas loga.
Uma falha ao notificar nunca derruba o script: o erro é só registrado no log.
"""

import logging
import socket

import requests

from . import config

log = logging.getLogger(__name__)


def notificar(mensagem: str, sucesso: bool) -> None:
    cfg = config.telegram()
    texto = f"{'✅' if sucesso else '❌'} Envio GfK ({socket.gethostname()})\n\n{mensagem}"

    if cfg is None:
        log.warning("Telegram não configurado; notificação não enviada: %s", texto)
        return

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{cfg.bot_token}/sendMessage",
            json={"chat_id": cfg.chat_id, "text": texto},
            timeout=30,
        )
        if not resp.ok:
            log.error("Telegram recusou a mensagem (%s): %s", resp.status_code, resp.text[:300])
            return
        log.info("Notificação enviada ao Telegram.")
    except requests.RequestException as erro:
        log.error("Falha ao notificar no Telegram: %s", erro)
