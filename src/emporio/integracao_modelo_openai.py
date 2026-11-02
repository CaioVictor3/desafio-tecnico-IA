from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError


class ProviderError(RuntimeError):
    pass


def mensagem_para_limite_da_api(erro: RateLimitError) -> str:
    """Distingue saldo/cota de limites temporários, sem expor a resposta bruta."""
    corpo = erro.body if isinstance(erro.body, dict) else {}
    corpo = corpo.get("error", corpo)
    corpo = corpo if isinstance(corpo, dict) else {}
    codigo = corpo.get("code")
    codigo = codigo if isinstance(codigo, str) else ""
    faturamento = (
        "[faturamento da API](https://platform.openai.com/settings/organization/billing/overview)"
    )
    causas = {
        "credit_balance_exhausted": (
            "Os créditos da organização OpenAI vinculada à chave acabaram "
            "(credit_balance_exhausted). Adicione créditos no "
            + faturamento
            + ". Aguardar ou reiniciar o chat não repõe o saldo."
        ),
        "project_spend_limit_exceeded": (
            "O projeto OpenAI atingiu seu limite de gastos (project_spend_limit_exceeded). "
            "Confira o limite nas configurações do projeto antes de tentar novamente."
        ),
        "organization_spend_limit_exceeded": (
            "A organização OpenAI atingiu seu limite de gastos "
            "(organization_spend_limit_exceeded). Confira o limite da organização "
            "antes de tentar novamente."
        ),
        "organization_usage_limit_exceeded": (
            "A organização atingiu o limite de uso aprovado pela OpenAI "
            "(organization_usage_limit_exceeded). Solicite a revisão do limite "
            "ao administrador da organização ou ao suporte da OpenAI."
        ),
    }
    # error.code é mais específico que error.type, que pode ser insufficient_quota.
    if codigo in causas:
        return causas[codigo]
    if codigo in {"insufficient_quota", "billing_hard_limit_reached"} or (
        corpo.get("type") == "insufficient_quota"
    ):
        return (
            "A conta da API OpenAI está sem cota disponível. Confira os créditos "
            "no " + faturamento + " e os limites do projeto/organização. "
            "É necessário regularizar a cota antes de tentar novamente."
        )
    if codigo in {"rate_limit_exceeded", "slow_down"} or (corpo.get("type") == "rate_limit_error"):
        espera = "Aguarde alguns instantes"
        try:
            segundos = float(erro.response.headers.get("retry-after", ""))
            if math.isfinite(segundos) and segundos >= 0:
                espera = f"Aguarde pelo menos {max(1, math.ceil(segundos))} segundos"
        except ValueError:
            pass
        return (
            "A OpenAI aplicou um limite temporário de requisições ou tokens. "
            + espera
            + " e tente novamente. Se persistir, confira os limites "
            "da organização e do projeto na plataforma OpenAI."
        )
    return (
        "A OpenAI retornou HTTP 429 sem uma causa específica reconhecida. "
        "Confira os créditos e os limites de requisições do projeto/organização "
        "antes de tentar novamente."
    )


@dataclass
class Turn:
    items: list[dict]
    text: str
    completed: bool = True


class Provider(Protocol):
    def generate(
        self, instructions: str, messages: list[dict], tools: list[dict], require_tool: bool = False
    ) -> Turn: ...


class OpenAIProvider:
    def __init__(self, api_key: str, model: str, client: OpenAI | None = None):
        if not api_key:
            raise ValueError("Configure OPENAI_API_KEY no .env para usar o atendimento.")
        self.model = model
        # O SDK repete HTTP 429 por padrão, inclusive falta de saldo. A interface
        # explica a causa e deixa a nova tentativa para o usuário após a correção.
        self.client = client or OpenAI(api_key=api_key, timeout=30.0, max_retries=0)

    def generate(
        self, instructions: str, messages: list[dict], tools: list[dict], require_tool: bool = False
    ) -> Turn:
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=messages,
                tools=tools,
                tool_choice="required" if require_tool else "auto",
                parallel_tool_calls=False,
                max_output_tokens=4000,
                store=False,
                include=["reasoning.encrypted_content"],
            )
        except RateLimitError as exc:
            raise ProviderError(mensagem_para_limite_da_api(exc)) from exc
        except (APIConnectionError, APITimeoutError) as exc:
            raise ProviderError("Não consegui conectar ao provedor. Tente novamente.") from exc
        except APIStatusError as exc:
            raise ProviderError(
                "O provedor recusou a solicitação. Confira a chave, o modelo "
                "e as permissões da conta."
            ) from exc
        return Turn(
            items=[item.model_dump(exclude_none=True) for item in response.output],
            text=response.output_text,
            completed=response.status == "completed",
        )
