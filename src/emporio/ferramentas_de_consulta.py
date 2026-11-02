from __future__ import annotations

import json
import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from emporio.repositorio_catalogo_e_pedidos import Catalog, DataError
from emporio.utilitarios_texto_e_moeda import cents


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class SearchProducts(Arguments):
    query: str = Field(max_length=150, description="Só termos do produto, sem a frase da pergunta.")
    category: str | None = Field(description="Nome da categoria, ex.: Violões; null para qualquer.")
    max_price_brl: float | None = Field(ge=0, le=1_000_000)
    only_available: bool
    limit: int = Field(ge=1, le=10)


class GetQuote(Arguments):
    product_id: int = Field(ge=1)


class GetOrder(Arguments):
    order_id: int = Field(ge=1)
    customer_email: str = Field(min_length=5, max_length=254)

    @field_validator("customer_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value.strip()):
            raise ValueError("Informe um e-mail válido.")
        return value.strip().casefold()


class GetAvailableInformation(Arguments):
    pass


DEFINITIONS = {
    "search_products": (
        SearchProducts,
        "Consultar catálogo, estoque e promoções ATUAIS no "
        "snapshot local. Inclua indisponíveis para perguntas sobre modelo específico.",
    ),
    "get_quote": (
        GetQuote,
        "Consultar preço e promoção ativa do produto. Não há regras de PIX, "
        "parcelamento ou frete disponíveis. Não faz compra.",
    ),
    "get_order": (
        GetOrder,
        "Consultar UM pedido com número e e-mail informados pelo próprio "
        "cliente. Nunca adivinhe o e-mail. Não há acesso ao cadastro/lista de clientes.",
    ),
    "get_available_information": (
        GetAvailableInformation,
        "Consultar as categorias e quais informações estão disponíveis. "
        "Use para saudações, limites de escopo e informações ausentes; "
        "não há políticas, endereço ou horários nos dados disponíveis.",
    ),
}


def schemas() -> list[dict]:
    result = []
    for name, (model, description) in DEFINITIONS.items():
        schema = model.model_json_schema()
        schema["required"] = list(schema["properties"])
        result.append(
            {
                "type": "function",
                "name": name,
                "description": description,
                "parameters": schema,
                "strict": True,
            }
        )
    return result


class Toolbox:
    def __init__(self, catalog: Catalog, today: date):
        self.catalog = catalog
        self.today = today

    def execute(
        self, name: str, raw_arguments: str, user_messages: list[str] | None = None
    ) -> dict:
        if name not in DEFINITIONS:
            return {"error": "unknown_tool", "message": "Ferramenta não permitida."}
        try:
            arguments = DEFINITIONS[name][0].model_validate_json(raw_arguments)
            match arguments:
                case SearchProducts():
                    return self.catalog.search(
                        query=arguments.query,
                        category=arguments.category,
                        max_price_cents=(
                            cents(str(arguments.max_price_brl))
                            if arguments.max_price_brl is not None
                            else None
                        ),
                        only_available=arguments.only_available,
                        limit=arguments.limit,
                    )
                case GetQuote():
                    return self.catalog.quote(**arguments.model_dump())
                case GetOrder():
                    # Identidade deve vir do cliente, nunca dos documentos nem da imaginação do LLM.
                    provided = {
                        email.casefold()
                        for text in (user_messages or [])
                        for email in re.findall(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", text)
                    }
                    if arguments.customer_email not in provided:
                        return {
                            "error": "identity_required",
                            "message": "Peça o e-mail de compra "
                            "ao cliente antes de consultar o pedido.",
                        }
                    return self.catalog.order(arguments.order_id, arguments.customer_email)
                case GetAvailableInformation():
                    return self.catalog.available_information()
        except ValidationError:
            # Não retornar os argumentos pessoais ou detalhes internos no erro de validação.
            return {
                "error": "invalid_arguments",
                "message": "Argumentos inválidos. Confira o "
                "schema, as datas e os campos obrigatórios da ferramenta.",
            }
        except (DataError, OSError, ValueError):
            return {
                "error": "source_unavailable",
                "message": "Não consegui confirmar essa informação agora. "
                "Não confirme valores ou prazos; oriente o cliente a falar com a equipe.",
            }
        return {"error": "unknown_tool"}

    def run(self, name: str, user_messages: list[str] | None = None, **kwargs) -> dict:
        """Entrada Python com a mesma validação usada nas chamadas do LLM."""
        return self.execute(name, json.dumps(kwargs, ensure_ascii=False), user_messages)
