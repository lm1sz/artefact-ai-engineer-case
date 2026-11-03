"""Safe rate-limit metadata. Never retain arbitrary provider error bodies."""
import json
import re

from .agent import ProviderError


def segundos(value: str) -> float | None:
    """Parse Groq durations such as 1m2.5s, 300ms or Retry-After: 12."""
    if not value:
        return None
    if re.fullmatch(r'\d+(?:\.\d+)?', value):
        return float(value)
    parts = re.findall(r'(\d+(?:\.\d+)?)(ms|h|m|s)', value)
    if ''.join(n+unit for n, unit in parts) != value:
        return None
    units = {'h': 3600, 'm': 60, 's': 1, 'ms': .001}
    return sum(float(n)*units[unit] for n, unit in parts)


class RateLimitError(ProviderError):
    def __init__(self, reason: str, retry_after: float | None, limits: dict | None = None):
        self.reason = reason
        self.retry_after = retry_after
        self.limits = limits or {}
        if reason == 'request_too_large':
            message = 'O histórico ou a mensagem excede o limite de tokens desta conta. Inicie uma nova conversa ou reduza a mensagem.'
        elif reason in ('tokens_per_day', 'requests_per_day'):
            message = 'A cota diária da Groq foi atingida. Aguarde a renovação da cota no painel da conta.'
        else:
            delay = max(1, int(retry_after or 30) + 1)
            message = f'Limite temporário da Groq (HTTP 429). Aguarde aproximadamente {delay} segundos antes de tentar novamente.'
        super().__init__(message)


def interpretar_429(headers, body: bytes) -> RateLimitError:
    retry = segundos(headers.get('retry-after', '')) if headers else None
    try:
        message = str(json.loads(body).get('error', {}).get('message', '')).lower()
    except (ValueError, AttributeError):
        message = ''
    reason = 'quota_unknown'
    for phrase, code in (('request too large', 'request_too_large'), ('tokens per day', 'tokens_per_day'),
                         ('requests per day', 'requests_per_day'), ('tokens per minute', 'tokens_per_minute'),
                         ('requests per minute', 'requests_per_minute')):
        if phrase in message:
            reason = code
            break
    if retry is None:
        match = re.search(r'try again in\s+([\d.hms]+)', message)
        retry = segundos(match[1]) if match else None
    limits = {label.lower(): float(number) for label, number in
              re.findall(r'\b(limit|used|requested):?\s*([0-9]+(?:\.[0-9]+)?)', message)}
    if reason in ('request_too_large', 'tokens_per_day', 'requests_per_day'):
        retry = None  # Repeating the same request cannot repair an oversized input/daily quota.
    elif retry is None:
        retry = 30
    return RateLimitError(reason, retry, limits)
