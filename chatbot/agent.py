"""Coordena a conversa e limita as chamadas de ferramentas.
Coordinate the conversation and bound tool calls."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .tools import Tools

# Lê as instruções na mesma pasta deste arquivo.
# Read instructions from the same directory as this file.
SYSTEM = Path(__file__).with_name("prompt.txt").read_text(encoding="utf-8")


class ProviderError(RuntimeError):
    pass


class Provider(Protocol):
    def responder(self, *, instructions: str, items: list[dict], tool_choice: str) -> dict:
        """Envia instrucoes e contexto ao modelo e retorna a resposta no formato do agente.
        Send instructions and context to the model and return the agent response format.
        """
        ...


@dataclass
class Reply:
    text: str
    tools: list[str]


class Agent:
    def __init__(self, tools: Tools, provider: Provider):
        """Recebe ferramentas e provedor e inicia o historico vazio.
        Receive tools and provider and start with empty history."""
        
        self.tools = tools
        self.provider = provider
        self.turns: list[list[dict]] = []

    def limpar_historico(self) -> None:
        """Apaga a conversa em memoria; preserva a sessao e o contador de acessos negados.
        Clear in-memory conversation; preserve the session and denied-access counter."""
        
        self.turns.clear()

    def perguntar(self, message: str) -> Reply:
        """Coordena uma mensagem: valida, consulta ferramentas e retorna a resposta.
        Coordinate one message: validate input, consult tools and return the reply."""
        
        # 1. Rejeita entradas vazias ou muito longas antes de chamar a API.
        # 1. Reject empty or oversized inputs before calling the API.
        if not message.strip() or len(message) > 4000:
            return Reply("Envie uma mensagem entre 1 e 4.000 caracteres.", [])
        # 2. Mascara dados pessoais reconhecidos antes de enviar a mensagem.
        # 2. Mask recognized personal data before sending the message.
        clean = self.tools.store.mascarar_dados(message)
        # 3. Recupera seis turnos de texto; resultados antigos de ferramentas são descartados.
        # 3. Retrieve six text turns; old tool results are discarded.
        history = [item for turn in self.turns[-6:] for item in turn]
        current = [{"role": "user", "content": clean}]
        used: list[str] = []
        instructions = SYSTEM + f"\nRuntime date: {self.tools.today}. Session authenticated: {self.tools.session.customer_id is not None}."
        # 4. Limita as rodadas; a primeira exige consulta a uma ferramenta.
        # 4. Bound model rounds; the first requires a tool call.
        for step in range(6):
            response = self.provider.responder(instructions=instructions, items=history + current,
                                             tool_choice="required" if step == 0 else "auto")
            # 5. Verifica a conclusão e o formato da resposta do provedor.
            # 5. Check provider response completion and format.
            if response.get("status") != "completed":
                raise ProviderError("The model did not complete its response. Retry or reduce the request.")
            output = response.get("output")
            if not isinstance(output, list) or not all(isinstance(item, dict) for item in output):
                raise ProviderError("Provider response had no valid output.")
            calls = [item for item in output if item.get("type") == "function_call"]
            # 6. Limita o total de ferramentas executadas para esta mensagem.
            # 6. Limit the total tool calls executed for this message.
            if len(calls) + len(used) > 10:
                raise ProviderError("Tool budget reached. Please narrow the question.")
            if calls:
                # Preserva o conteúdo original exigido pelo protocolo de continuação.
                # Preserve original content required by the continuation protocol.
                current.extend(output)
                for call in calls:
                    if not isinstance(call.get("call_id"), str) or not isinstance(call.get("name"), str):
                        raise ProviderError("Provider returned a malformed tool call.")
                    try:
                        args = json.loads(call.get("arguments", ""))
                    except (json.JSONDecodeError, TypeError):
                        args = None
                    # 7. Delega a validação e a operação ao conjunto de ferramentas.
                    # 7. Delegate validation and execution to the tool collection.
                    result = self.tools.executar(call["name"], args)
                    used.append(call["name"])
                    # 8. Associa o resultado à chamada e o devolve ao modelo na próxima rodada.
                    # 8. Associate the result with its call and return it on the next round.
                    current.append({"type": "function_call_output", "call_id": call["call_id"],
                                    "output": json.dumps(result, ensure_ascii=False)})
                continue
            if not used:
                raise ProviderError("The model skipped required source consultation. Please retry.")
            # 9. Extrai a resposta final e mascara novamente os dados reconhecidos.
            # 9. Extract the final answer and mask recognized personal data again.
            texts = []
            for item in output:
                if item.get("type") != "message":
                    continue
                parts = item.get("content", [])
                if not isinstance(parts, list) or not all(isinstance(part, dict) for part in parts):
                    raise ProviderError("Provider returned malformed message content. Please retry.")
                for part in parts:
                    if part.get("type") == "output_text":
                        if not isinstance(part.get("text"), str):
                            raise ProviderError("Provider returned invalid answer text. Please retry.")
                        texts.append(part["text"])
            text = self.tools.store.mascarar_dados("\n".join(texts)).strip()
            if not text:
                raise ProviderError("The provider returned no answer. Please retry.")
            # 10. Guarda apenas pergunta e resposta e retorna o texto com as ferramentas usadas.
            # 10. Store only question and answer; return text and the tool names used.
            self.turns.append([{"role": "user", "content": clean}, {"role": "assistant", "content": text}])
            self.turns = self.turns[-6:]
            return Reply(text, used)
        raise ProviderError("Tool budget reached. Please narrow the question.")
