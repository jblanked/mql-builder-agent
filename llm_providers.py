from dataclasses import dataclass

import requests

from api_keys import OPENAI_API_KEY, DEEPSEEK_API_KEY


@dataclass
class LLMProvider:
    """LLM provider config with endpoint URL, model name, and API key."""

    id: str
    label: str
    model: str
    url: str
    api_key: str


PROVIDERS: dict[str, LLMProvider] = {
    "openai": LLMProvider(
        id="openai",
        label="OpenAI",
        model="gpt-5.4-mini",
        url="https://api.openai.com/v1/chat/completions",
        api_key=OPENAI_API_KEY,
    ),
    "deepseek": LLMProvider(
        id="deepseek",
        label="DeepSeek",
        model="deepseek-v4-flash",
        url="https://api.deepseek.com/chat/completions",
        api_key=DEEPSEEK_API_KEY,
    ),
}

# Default provider
PROVIDER: LLMProvider = PROVIDERS["deepseek"]

def post_chat_completion(payload):
    """Send a chat completion request and return the response."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {PROVIDER.api_key}",
    }
    response = requests.post(PROVIDER.url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()
