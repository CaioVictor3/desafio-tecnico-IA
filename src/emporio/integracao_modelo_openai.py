from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError


class ProviderError(RuntimeError):
    pass


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
            raise ValueError("Configure OPENAI_API_KEY no .env ou use --provider demo.")
        self.model = model
        self.client = client or OpenAI(api_key=api_key, timeout=30.0, max_retries=2)

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
            raise ProviderError(
                "O provedor limitou a solicitação. Confira a cota ou tente "
                "novamente em alguns instantes."
            ) from exc
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
