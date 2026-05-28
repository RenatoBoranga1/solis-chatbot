import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.field_encryption_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_value(value: str | None) -> str | None:
    if not value:
        return value
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str | None) -> str | None:
    if not value:
        return value
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


LGPD_CONSENT_MESSAGE = (
    "Para continuar, vou coletar algumas informações de contato e dados da instalação. "
    "Esses dados serão usados apenas para atendimento, orçamento ou suporte da Solar Soluções, "
    "conforme a política de privacidade da empresa. Tudo bem?"
)
