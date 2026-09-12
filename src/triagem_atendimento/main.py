from __future__ import annotations

import sys
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from triagem_atendimento.graph import build_graph


def main() -> None:
    graph = build_graph()
    config = {"configurable": {"thread_id": "cli-session"}}

    print("=== Atendimento Automático Iniciado (Ctrl+C para encerrar) ===\n")

    while True:
        try:
            user_input = input("\nCliente: ").strip()
            if not user_input:
                continue

            current_input = {"messages": [HumanMessage(content=user_input)]}

            while True:
                result = graph.invoke(current_input, config=config)

                # Verifica se a execução pausou por interrupt do HITL
                if "__interrupt__" in result:
                    interrupt_info = result["__interrupt__"][0].value
                    motivo = interrupt_info.get("motivo", "Sem motivo especificado")

                    print(f"\n[INTERRUPÇÃO DE SEGURANÇA / ESCALAÇÃO DETECTADA]")
                    print(f"Motivo informado pelo agente: {motivo}")

                    escolha = input("Deseja aprovar a escalação para atendente humano? (s/n): ").strip().lower()
                    aprovado = escolha == "s"

                    observacao = None
                    if not aprovado:
                        obs_input = input("Instrução adicional para o agente (opcional, Enter para pular): ").strip()
                        observacao = obs_input if obs_input else None

                    # Prepara o Command de retomada para a próxima iteração do ciclo
                    current_input = Command(
                        resume={
                            "aprovado": aprovado,
                            "observacao": observacao,
                        }
                    )
                    continue

                # Sem interrupções pendentes: exibe a mensagem final do agente
                messages = result.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    content = last_message.content
                    if isinstance(content, list):
                        # Extrai os blocos de texto caso venha como lista de dicts
                        texto = "".join(
                            bloco["text"] for bloco in content if isinstance(bloco, dict) and "text" in bloco
                        )
                        print(f"\nAgente: {texto}")
                    else:
                        print(f"\nAgente: {content}")
                break

        except KeyboardInterrupt:
            print("\nEncerrando atendimento...")
            sys.exit(0)


if __name__ == "__main__":
    main()