"""OpenRouter chat-completions client."""

import json
import logging
import re

import requests
from django.conf import settings

from ai.exceptions import AINotConfigured, AIRequestFailed

logger = logging.getLogger(__name__)


def is_ai_configured() -> bool:
    return bool(getattr(settings, 'OPENROUTER_API_KEY', ''))


def chat_completion(
    messages: list[dict],
    *,
    json_mode: bool = False,
    temperature: float = 0.2,
    max_tokens: int = 1200,
) -> str:
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    if not api_key:
        raise AINotConfigured(
            'Service IA non configuré. Définissez OPENROUTER_API_KEY et OPENROUTER_MODEL dans .env.',
        )

    model = getattr(settings, 'OPENROUTER_MODEL', 'openai/gpt-4o-mini')
    base_url = getattr(settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1').rstrip('/')

    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    if json_mode:
        payload['response_format'] = {'type': 'json_object'}

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': getattr(settings, 'OPENROUTER_HTTP_REFERER', 'https://vora.cm'),
        'X-Title': 'VORA Platform',
    }

    try:
        response = requests.post(
            f'{base_url}/chat/completions',
            headers=headers,
            json=payload,
            timeout=getattr(settings, 'OPENROUTER_TIMEOUT_SECONDS', 45),
        )
        response.raise_for_status()
        data = response.json()
        content = data['choices'][0]['message']['content']
        return content.strip()
    except requests.RequestException as exc:
        logger.exception('OpenRouter request failed')
        detail = str(exc)
        if hasattr(exc, 'response') and exc.response is not None:
            try:
                detail = exc.response.text[:500]
            except Exception:
                pass
        raise AIRequestFailed(f'Échec appel OpenRouter: {detail}') from exc
    except (KeyError, IndexError, TypeError) as exc:
        raise AIRequestFailed('Réponse OpenRouter invalide.') from exc


def parse_json_response(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIRequestFailed('Le modèle n\'a pas renvoyé du JSON valide.') from exc
