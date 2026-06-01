from urllib.parse import urlparse


BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def validate_safe_url(url: str | None) -> str | None:
    if url is None:
        return None

    value = url.strip()
    if not value:
        return None

    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("URL deve começar com https://")

    hostname = (parsed.hostname or "").lower()
    if hostname in BLOCKED_HOSTS or hostname.endswith(".local"):
        raise ValueError("URL não permitida")

    if parsed.username or parsed.password:
        raise ValueError("URL não deve conter credenciais")

    return value


def is_youtube_url(url: str | None) -> bool:
    if not url:
        return False
    hostname = (urlparse(url).hostname or "").lower()
    return hostname in {"youtube.com", "www.youtube.com", "youtu.be"}
