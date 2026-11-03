"""Adaptador REST da Groq para GPT-OSS 120B e ferramentas locais.
Groq REST adapter for GPT-OSS 120B and local tools.
"""
import json
import threading
from time import monotonic, sleep
import urllib.error
import urllib.request

from .agent import ProviderError
from .tools import SCHEMAS
from .rate_limits import interpretar_429, segundos

MODELO_GROQ = "openai/gpt-oss-120b"


def _schema_groq(schema):
    """Keep wire schemas permissive; enforce every original constraint in Python."""
    if isinstance(schema, list):
        return [_schema_groq(s) for s in schema]
    if not isinstance(schema, dict):
        return schema
    result = {k: _schema_groq(v) for k, v in schema.items()
              if k not in ("minimum", "maximum", "additionalProperties")}
    if "minimum" in schema or "maximum" in schema:
        result["description"] = (schema.get("description", "") +
            f" Allowed bounds: {schema.get('minimum', 0)} to {schema.get('maximum', 10**9)}.").strip()
    return result


class GroqProvider:
    # The agent retrieves real store context before allowing a tool-free reply.
    source_bootstrap = True
    def __init__(self, api_key: str, model: str = MODELO_GROQ, reasoning: str = "medium"):
        if not api_key or not api_key.strip():
            raise ValueError("Set GROQ_API_KEY in chatbot/.env or your environment.")
        if model != MODELO_GROQ:
            raise ValueError(f"The Groq adapter currently supports only {MODELO_GROQ}.")
        if reasoning not in ("low", "medium", "high"):
            raise ValueError("GROQ_REASONING_EFFORT must be low, medium or high.")
        self.api_key, self.model, self.reasoning = api_key, model, reasoning
        self._lock = threading.Lock()
        self._remaining_tokens = None
        self._reset_at = 0.0
        self.diagnostics = {'request_count': 0, 'rate_limit_retries': 0,
                            'proactive_wait_seconds': 0.0, 'observed_limits': {},
                            'rate_limit_events': [], 'usage': {}}

    def _registrar_limites(self, headers):
        if not headers:
            return
        allowed = {f'x-ratelimit-{kind}-{unit}' for kind in ('limit', 'remaining', 'reset')
                   for unit in ('requests', 'tokens')}
        safe = {k.lower(): v for k, v in headers.items() if k.lower() in allowed}
        self.diagnostics['observed_limits'].update(safe)
        remaining = safe.get('x-ratelimit-remaining-tokens', '')
        if str(remaining).isdigit():
            self._remaining_tokens = int(remaining)
            self._reset_at = monotonic() + (segundos(safe.get('x-ratelimit-reset-tokens', '')) or 0)

    def _aguardar_capacidade(self, payload):
        # A conservative estimate only schedules waiting; it never changes the
        # prompt, clears history or claims to be an exact tokenizer.
        estimate = len(json.dumps(payload, ensure_ascii=False)) // 4 + 512
        wait = self._reset_at - monotonic()
        if self._remaining_tokens is not None and self._remaining_tokens < estimate and 0 < wait <= 60:
            sleep(wait + .25)
            self.diagnostics['proactive_wait_seconds'] += round(wait + .25, 3)
            self._remaining_tokens = None

    @staticmethod
    def _mensagens(instructions: str, items: list[dict]) -> list[dict]:
        messages = [{"role": "system", "content": instructions}]
        for item in items:
            if item.get("type") == "groq_message":
                messages.append(item["message"])
            elif item.get("type") == "function_call_output":
                messages.append({"role": "tool", "tool_call_id": item["call_id"],
                                 "content": item["output"]})
            elif item.get("role") in ("user", "assistant"):
                messages.append({"role": item["role"], "content": item["content"]})
            # Normalized function_call records are represented by groq_message.
        return messages

    def responder(self, *, instructions: str, items: list[dict], tool_choice: str) -> dict:
        payload = {"model": self.model, "messages": self._mensagens(instructions, items),
                   "tools": [{"type": "function", "function": {
                       "name": t["name"], "description": t["description"],
                       "parameters": _schema_groq(t["parameters"])}} for t in SCHEMAS],
                   "tool_choice": tool_choice,
                   "parallel_tool_calls": False,
                   "reasoning_effort": self.reasoning, "include_reasoning": False,
                   "max_completion_tokens": 2048, "stream": False}
        if tool_choice == 'none':
            # A language-only repair has no tools or source pages to execute.
            payload.pop('tools')
            payload.pop('parallel_tool_calls')
        request = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(payload).encode(), method="POST",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
                     "User-Agent": "EmporioAgent/0.1"})
        with self._lock:
            self._aguardar_capacidade(payload)
            for attempt in range(2):
                self.diagnostics['request_count'] += 1
                try:
                    with urllib.request.urlopen(request, timeout=45) as response:
                        self._registrar_limites(getattr(response, 'headers', None))
                        result = json.load(response)
                    if isinstance(result, dict):
                        usage = result.get('usage') or {}
                        for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
                            value = usage.get(key) if isinstance(usage, dict) else None
                            if isinstance(value, int):
                                self.diagnostics['usage'][key] = self.diagnostics['usage'].get(key, 0) + value
                    break
                except urllib.error.HTTPError as error:
                    self._registrar_limites(error.headers)
                    if error.code == 429:
                        rate_error = interpretar_429(error.headers, error.read())
                        self.diagnostics['rate_limit_events'].append({
                            'reason': rate_error.reason, 'retry_after': rate_error.retry_after,
                            'limits': rate_error.limits})
                        if attempt == 0 and rate_error.retry_after is not None and rate_error.retry_after <= 60:
                            # Only retry a rejected HTTP request once. Daily quotas
                            # and oversized requests cannot be repaired by waiting.
                            self.diagnostics['rate_limit_retries'] += 1
                            sleep(rate_error.retry_after + .25)
                            continue
                        raise rate_error from None
                    raise ProviderError(f"Groq request failed (HTTP {error.code}). Check key, model access and request configuration locally.") from None
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                    raise ProviderError("Could not reach Groq or decode its response. Check network access and retry.") from None
        return self._normalizar(result)

    @staticmethod
    def _normalizar(result: object) -> dict:
        choices = result.get("choices") if isinstance(result, dict) else None
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ProviderError("Groq returned no valid candidate.")
        choice = choices[0]
        if choice.get("finish_reason") not in ("stop", "tool_calls"):
            raise ProviderError("Groq did not complete the response. Try a shorter question.")
        message = choice.get("message")
        if not isinstance(message, dict):
            raise ProviderError("Groq returned malformed message content.")
        calls = message.get("tool_calls")
        if calls is None:
            calls = []
        if not isinstance(calls, list):
            raise ProviderError("Groq returned malformed tool calls.")
        if calls:
            output = []
            native = []
            for call in calls:
                if not isinstance(call, dict) or call.get("type") != "function":
                    raise ProviderError("Groq returned a malformed tool call.")
                function = call.get("function")
                if (not isinstance(function, dict)
                    or not all(isinstance(v, str) and v for v in (call.get("id"), function.get("name")))
                    or not isinstance(function.get("arguments"), str)):
                    raise ProviderError("Groq returned invalid tool-call fields.")
                native.append({"id": call["id"], "type": "function", "function": {
                    "name": function["name"], "arguments": function["arguments"]}})
                output.append({"type": "function_call", "call_id": call["id"],
                               "name": function["name"], "arguments": function["arguments"]})
            # Preserve only protocol fields; never display or store reasoning text.
            return {"status": "completed", "output": [{"type": "groq_message", "message": {
                "role": "assistant", "content": None, "tool_calls": native}}, *output]}
        text = message.get("content")
        if choice["finish_reason"] != "stop" or not isinstance(text, str) or not text.strip():
            raise ProviderError("Groq returned no final answer.")
        return {"status": "completed", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": text}]}]}
