"""Local CLI; demo identity is explicit and cannot be changed through chat."""
from __future__ import annotations

import argparse
import json
import os

from .agent import Agent, ProviderError
from .providers import criar_provedor, configuracao_provedor, carregar_ambiente
from .data import ROOT, Store, localizar_dados
from .tools import Session, Tools


def principal() -> None:
    """Configura o chatbot e executa a conversa pelo terminal.
    Configure the chatbot and run the terminal conversation.
    """
    parser = argparse.ArgumentParser(description="Empório da Música · Sua música começa aqui")
    parser.add_argument("--demo-customer-id", type=int, help="LOCAL DEMO ONLY: simulate an authenticated session.")
    parser.add_argument("--check", action="store_true", help="Validate source data without an API key.")
    parser.add_argument("--ask", dest="pergunta", help="Ask one question, then exit.")
    parser.add_argument("--trace", action="store_true", help="Display tool names only (no arguments or records).")
    args = parser.parse_args()
    carregar_ambiente(ROOT / ".env")
    try:
        store = Store(localizar_dados(os.getenv("EMPORIO_DATA_DIR") or None))
        if args.check:
            settings = configuracao_provedor()
            print(json.dumps({"tables": {k: len(v) for k, v in store.tables.items()},
                              "policy_pages": len(store.paginas_politica),
                              **settings, "model_configured": bool(settings["model"]),
                              "api_connectivity_tested": False}, indent=2))
            return
        if args.demo_customer_id is not None and args.demo_customer_id not in store.customers:
            parser.error("Unknown demo customer id.")
        provider = criar_provedor()
        agent = Agent(Tools(store, Session(args.demo_customer_id)), provider)
    except (ValueError, OSError, ImportError) as error:
        parser.exit(2, f"Setup error: {error}\n")
    print("Empório da Música · Sua música começa aqui.")
    print("Dados de demonstração; sem conexão com pedidos ou transportadoras reais.")
    if args.demo_customer_id is not None:
        print("Sessão autenticada SIMULADA localmente. Não é autenticação de produção.")
    if args.pergunta is None:
        print("/reset limpa o histórico; /quit encerra. Não envie dados pessoais ou senhas.")
    while True:
        try:
            message = args.pergunta if args.pergunta is not None else input("\nVocê: ")
            if message.strip() == "/quit":
                break
            if message.strip() == "/reset":
                agent.limpar_historico()
                print("Histórico limpo.")
                if args.pergunta is not None:
                    break
                continue
            reply = agent.perguntar(message)
            print(f"\nAssistente: {reply.text}")
            if args.trace:
                print("Ferramentas: " + ", ".join(reply.tools))
        except ProviderError as error:
            print(f"Não consegui concluir o atendimento: {error}")
            if args.pergunta is not None:
                raise SystemExit(1)
        except (EOFError, KeyboardInterrupt):
            print("\nAté mais!")
            break
        if args.pergunta is not None:
            break


if __name__ == "__main__":
    principal()
