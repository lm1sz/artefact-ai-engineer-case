"""OpenAI Responses transport and configuration for gpt-6.1-sol."""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .agent import Provider, ProviderError
from .tools import SCHEMAS

MODELO = "gpt-6.1-sol"
ESFORCOS = ("", "low", "medium", "high", "xhigh", "max")


def carregar_ambiente(path: Path) -> None:
    """Le pares KEY=value sem executar comandos nem sobrescrever o ambiente.
    """
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


class OpenAIProvider:
    def __init__(self, api_key: str, model: str = MODELO, reasoning: str = "medium"):
        """Valida configuracao OpenAI e guarda credenciais apenas na instancia.
        """
        if not api_key or not api_key.strip():
            raise ValueError("Set OPENAI_API_KEY in chatbot/.env or your environment.")
        if model != MODELO:
            raise ValueError(f"This chatbot uses only {MODELO}. Check OPENAI_MODEL locally.")
        if reasoning not in ESFORCOS:
            raise ValueError("Unsupported OPENAI_REASONING_EFFORT setting.")
        self.api_key, self.model, self.reasoning = api_key, model, reasoning

    def responder(self, *, instructions: str, items: list[dict], tool_choice: str) -> dict:
        """Envia instrucoes e contexto ao modelo e retorna a resposta no formato do agente.
        """
        payload = {"model": self.model, "instructions": instructions,
                   "input": items, "tools": SCHEMAS, "tool_choice": tool_choice,
                   "parallel_tool_calls": False, "store": False,
                   "include": ["reasoning.encrypted_content"], "max_output_tokens": 4000}
        if self.reasoning:
            payload["reasoning"] = {"effort": self.reasoning}
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses", data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.load(response)
            if not isinstance(result, dict):
                raise ProviderError("Provider returned an invalid response.")
            return result
        except urllib.error.HTTPError as error:
            # Do not echo error bodies: they may contain input, credentials or private context.
            raise ProviderError(f"Provider request failed (HTTP {error.code}). Check model access, reasoning setting, quota, and key locally.", status_code=error.code) from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            raise ProviderError("Could not reach the provider or decode its response. Please retry.") from None


def configuracao_provedor() -> dict:
    """Le o provedor e modelo escolhidos sem expor a chave da API.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider != "openai":
        raise ValueError("LLM_PROVIDER must be openai.")
    model = os.getenv("OPENAI_MODEL", MODELO).strip()
    reasoning = os.getenv("OPENAI_REASONING_EFFORT", "medium").strip()
    if model != MODELO:
        raise ValueError(f"This chatbot uses only {MODELO}. Check OPENAI_MODEL locally.")
    if reasoning not in ESFORCOS:
        raise ValueError("Unsupported OPENAI_REASONING_EFFORT setting.")
    return {"provider": "openai", "model": MODELO, "reasoning_effort": reasoning,
            "api_key_configured": bool(os.getenv("OPENAI_API_KEY", "").strip())}


def criar_provedor() -> Provider:
    """Instancia apenas o provedor configurado, sem troca automatica em falhas.
    """
    settings = configuracao_provedor()
    return OpenAIProvider(os.getenv("OPENAI_API_KEY", ""), settings["model"],
                          settings["reasoning_effort"])
