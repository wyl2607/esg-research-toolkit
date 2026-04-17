from openai import OpenAI

from core.config import settings
from core.models import get as get_model_name
from core.models import get_spec

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    return _client


def complete(system: str, user: str, max_tokens: int | None = None) -> str:
    extraction_spec = get_spec("extraction")
    response = get_client().chat.completions.create(
        model=get_model_name("extraction"),
        max_tokens=max_tokens or extraction_spec.max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (response.choices[0].message.content or "").strip()
