"""Envio do arquivo gerado para o servidor FTP (com suporte opcional a FTPS)."""

import logging
import ssl
from ftplib import FTP, FTP_TLS
from pathlib import Path

from .config import FtpConfig

log = logging.getLogger(__name__)


def _conectar(cfg: FtpConfig) -> FTP:
    ftp = FTP_TLS() if cfg.usar_tls else FTP()
    ftp.connect(cfg.host, cfg.porta, timeout=60)
    ftp.login(cfg.usuario, cfg.senha)
    if cfg.usar_tls:
        ftp.prot_p()  # criptografa também o canal de dados
    ftp.cwd(cfg.diretorio)
    return ftp


def enviar(cfg: FtpConfig, arquivo: Path) -> None:
    with _conectar(cfg) as ftp, arquivo.open("rb") as f:
        try:
            ftp.storbinary(f"STOR {arquivo.name}", f)
        except (ConnectionResetError, ssl.SSLError) as erro:
            # O FTP da GfK fecha o canal de dados sem o encerramento TLS; o arquivo
            # chega completo, mas o ftplib acusa erro. A conferência abaixo decide.
            log.warning("Conexão encerrada pelo servidor ao final do envio (%s); conferindo...", erro)

    # Confirma o envio comparando o tamanho remoto com o local (nova conexão)
    with _conectar(cfg) as ftp:
        remoto = ftp.size(arquivo.name)
    local = arquivo.stat().st_size
    if remoto != local:
        raise RuntimeError(f"Envio incompleto: {remoto} bytes no FTP, {local} bytes locais")
    log.info("Tamanho conferido no FTP: %d bytes.", remoto)
