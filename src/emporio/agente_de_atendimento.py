from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from emporio.ferramentas_de_consulta import Toolbox, schemas
from emporio.historico_de_conversas import History
from emporio.instrucoes_do_agente import SYSTEM_PROMPT
from emporio.integracao_modelo_openai import Provider, ProviderError


@dataclass
class Answer:
    text: str
    trace: list[dict] = field(default_factory=list)


class Agent:
    def __init__(self, provider: Provider, toolbox: Toolbox, history: History, max_rounds: int = 6):
        self.provider, self.toolbox, self.history = provider, toolbox, history
        self.max_rounds = max_rounds

    def reply(self, message: str) -> Answer:
        if not message.strip() or len(message) > 4000:
            return Answer("Envie uma mensagem entre 1 e 4.000 caracteres, por favor.")
        messages = self.history.load() + [{"role": "user", "content": message}]
        user_messages = [m["content"] for m in messages if m["role"] == "user"]
        instructions = SYSTEM_PROMPT + (
            f"\nData atual: {self.toolbox.today.isoformat()}. Fuso da loja: America/Campo_Grande."
        )
        trace: list[dict] = []
        for iteration in range(self.max_rounds):
            try:
                # Uma consulta inicial é obrigatória, inclusive para aprender o escopo da loja.
                turn = self.provider.generate(instructions, messages, schemas(), iteration == 0)
            except ProviderError as exc:
                return Answer(str(exc), trace)
            if not turn.completed:
                return Answer(
                    "A resposta do provedor ficou incompleta. Não consegui confirmar "
                    "sua solicitação; tente reformular a pergunta.",
                    trace,
                )
            messages.extend(turn.items)
            calls = [item for item in turn.items if item.get("type") == "function_call"]
            if not calls:
                if not turn.text.strip():
                    return Answer("Não consegui montar uma resposta. Pode reformular?", trace)
                if not trace:
                    return Answer("Não consegui confirmar essa informação agora. Tente novamente.")
                if not any(event["ok"] for event in trace):
                    return Answer(
                        "Não consegui confirmar sua solicitação agora. "
                        "Confira os dados informados ou fale com a equipe.",
                        trace,
                    )
                self.history.save_turn(message, turn.text)
                return Answer(turn.text, trace)
            if len(calls) > 4 or len(trace) + len(calls) > 12:
                break
            for call in calls:
                start = time.monotonic()
                result = self.toolbox.execute(
                    call.get("name", ""), call.get("arguments", "{}"), user_messages
                )
                # Trace não registra argumentos, e-mails, texto do cliente ou conteúdo dos pedidos.
                trace.append(
                    {
                        "tool": call.get("name"),
                        "ok": "error" not in result,
                        "duration_ms": round((time.monotonic() - start) * 1000),
                    }
                )
                messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": call["call_id"],
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
        return Answer(
            "Cheguei ao limite de consultas sem concluir. Pode dividir a pergunta? "
            "Não confirmei nenhuma alteração ou compra.",
            trace,
        )
