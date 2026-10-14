"""Envio do arquivo gerado para o servidor FTP (com suporte opcional a FTPS)."""

from ftplib import FTP, FTP_TLS
from pathlib import Path

from .config import FtpConfig


def enviar(cfg: FtpConfig, arquivo: Path) -> None:
    ftp = FTP_TLS() if cfg.usar_tls else FTP()
    ftp.connect(cfg.host, cfg.porta, timeout=60)
    try:
        ftp.login(cfg.usuario, cfg.senha)
        if cfg.usar_tls:
            ftp.prot_p()  # criptografa também o canal de dados
        ftp.cwd(cfg.diretorio)
        with arquivo.open("rb") as f:
            ftp.storbinary(f"STOR {arquivo.name}", f)
    finally:
        ftp.quit()
