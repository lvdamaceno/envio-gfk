"""Leitura das configurações a partir de variáveis de ambiente (arquivo .env)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome, "").strip()
    if not valor:
        raise RuntimeError(f"Variável de ambiente obrigatória ausente: {nome} (veja .env.example)")
    return valor


@dataclass(frozen=True)
class SankhyaConfig:
    base_url: str
    client_id: str
    client_secret: str
    x_token: str


@dataclass(frozen=True)
class FtpConfig:
    host: str
    porta: int
    usuario: str
    senha: str
    diretorio: str
    usar_tls: bool


def sankhya() -> SankhyaConfig:
    return SankhyaConfig(
        base_url=os.getenv("SANKHYA_BASE_URL", "https://api.sankhya.com.br").rstrip("/"),
        client_id=_obrigatoria("SANKHYA_CLIENT_ID"),
        client_secret=_obrigatoria("SANKHYA_CLIENT_SECRET"),
        x_token=_obrigatoria("SANKHYA_X_TOKEN"),
    )


def ftp() -> FtpConfig:
    return FtpConfig(
        host=_obrigatoria("FTP_HOST"),
        porta=int(os.getenv("FTP_PORTA", "21")),
        usuario=_obrigatoria("FTP_USUARIO"),
        senha=_obrigatoria("FTP_SENHA"),
        diretorio=os.getenv("FTP_DIRETORIO", "/"),
        usar_tls=os.getenv("FTP_TLS", "false").lower() in ("1", "true", "sim"),
    )
