"""Simulador determinístico para smoke tests. Não é um LLM nem substitui o modo OpenAI."""

from __future__ import annotations

import json
import re
from uuid import uuid4

from emporio.provider import Turn
from emporio.text import normalize

BRANDS = r"yamaha|tagima|giannini|rozini|shelby|crafter|martin|taylor|takamine|kala|ohana|kalani"


def call(name: str, **kwargs) -> Turn:
    return Turn(
        [
            {
                "type": "function_call",
                "name": name,
                "call_id": "demo_" + uuid4().hex,
                "arguments": json.dumps(kwargs, ensure_ascii=False),
            }
        ],
        "",
    )


def intent(text: str) -> str | None:
    if re.search(r"ignore|prompt|sql|liste.*clientes|todos.*clientes", text):
        return "scope"
    if re.search(r"arrepend|devol|defeito|troca", text):
        return "return"
    if re.search(r"pedido|rastre|[\w.+-]+@[\w.-]+", text):
        return "order"
    if re.search(r"endereco|horario|funciona|telefone|whatsapp|frete|garantia|pagamento", text):
        return "policy"
    if re.search(BRANDS + r"|violao|violoes|ukulele|guitarra|baixo|bateria|teclado", text):
        return "product"
    return None


class DemoProvider:
    def generate(
        self, instructions: str, messages: list[dict], tools: list[dict], require_tool: bool = False
    ) -> Turn:
        user_indices = [i for i, m in enumerate(messages) if m.get("role") == "user"]
        last = user_indices[-1]
        user_texts = [m["content"] for m in messages if m.get("role") == "user"]
        current = normalize(user_texts[-1])
        all_text = normalize(" ".join(user_texts))
        route = intent(current)
        if route is None:
            followup = re.search(r"^e\s|\bonline\b|\brecebi\b|\bsem uso\b|\b\d+\s*x\b", current)
            route = (
                next(
                    (
                        intent(normalize(t))
                        for t in reversed(user_texts[:-1])
                        if intent(normalize(t))
                    ),
                    "scope",
                )
                if followup
                else "scope"
            )
        outputs = [
            json.loads(m["output"])
            for m in messages[last + 1 :]
            if m.get("type") == "function_call_output"
        ]
        if outputs:
            if "error" in outputs[-1]:
                return Turn([], outputs[-1].get("message", "Não consegui confirmar a consulta."))
            if route == "product":
                found = outputs[0].get("products", [])
                if (
                    len(outputs) == 1
                    and len(found) == 1
                    and re.search(r"pix|parcela|\d+\s*x|credito|custa|preco", current)
                ):
                    installments = re.search(r"(\d+)\s*x", current)
                    return call(
                        "get_quote",
                        product_id=found[0]["product_id"],
                        payment_method="pix" if "pix" in current else "credit",
                        installments=int(installments[1]) if installments else 1,
                    )
                return Turn([], self._products(outputs))
            if route == "order":
                result = outputs[-1]
                if "order_id" not in result:
                    return Turn(
                        [],
                        "Para consultar seu pedido, me informe o número e o e-mail "
                        "usado na compra, por favor.",
                    )
                status = {
                    "shipped": "enviado",
                    "confirmed": "confirmado",
                    "pending": "pendente",
                    "delivered": "entregue",
                    "cancelled": "cancelado",
                }[result["status"]]
                answer = (
                    f"Seu pedido #{result['order_id']} está {status}. Total: {result['total']}."
                )
                if result["tracking_code"]:
                    answer += f" Código informado na base: {result['tracking_code']}."
                if result["estimated_delivery"]:
                    answer += f" Previsão registrada: {result['estimated_delivery']}."
                if result["notes"]:
                    answer += f" Observação: {result['notes']}."
                return Turn(
                    [],
                    answer + " Consultei o snapshot local de orders.csv; não fiz "
                    "consulta à transportadora. Previsão não comprova data de recebimento.",
                )
            if route == "return":
                result = outputs[-1]
                if "question" in result:
                    return Turn([], result["question"])
                answer = (
                    f"Pelo manual, o prazo desta situação termina em {result['deadline']} "
                    f"({result['elapsed_days']} dias decorridos). "
                )
                answer += (
                    "Você está dentro da janela de solicitação. "
                    if result["within_window"]
                    else "A janela descrita no manual passou; a equipe deve avaliar seu caso. "
                )
                return Turn(
                    [],
                    answer + result["next_step"] + " Isso é uma orientação: não "
                    "registrei nem aprovei devolução. Fonte: manual, seção "
                    + result["policy_sources"][0]["section"]
                    + ".",
                )
            if route == "policy":
                matches = outputs[-1].get("matches", [])
                if "endereco" in current:
                    section = next((s for s in matches if s["section"] == "1.2"), None)
                    if section:
                        address = next(
                            (
                                line.removeprefix("Endereço ")
                                for line in section["text"].splitlines()
                                if line.startswith("Endereço ")
                            ),
                            None,
                        )
                        if address:
                            return Turn(
                                [], f"A loja fica na {address}. Fonte: manual, seção 1.2, página 2."
                            )
                if re.search(r"horario|funciona", current):
                    section = next((s for s in matches if s["section"] == "2"), None)
                    if section:
                        hours = [
                            line
                            for line in section["text"].splitlines()
                            if line.startswith(("Segunda ", "Sábado ", "Domingo "))
                        ]
                        return Turn(
                            [],
                            "Horário regular da loja e WhatsApp:\n- "
                            + "\n- ".join(hours)
                            + "\nDatas especiais podem ter alterações. "
                            "Fonte: manual, seção 2, página 2.",
                        )
                matches = matches[:1]
                text = "\n\n".join(
                    f"{s['title']} (manual, seção {s['section']}, "
                    f"p. {','.join(map(str, s['pages']))}):\n{s['text']}"
                    for s in matches
                )
                if re.search(r"telefone|whatsapp|email|e-mail", current):
                    text += "\nAtenção: " + outputs[-1]["ambiguities"][0]
                return Turn([], text or "Não encontrei essa informação no manual.")
            return Turn(
                [],
                "Sou a Mel, assistente virtual da Empório da Música. Posso ajudar "
                "com instrumentos, pedidos e políticas da loja. A loja trabalha só com "
                "instrumentos, sem acessórios. Não compartilho cadastros de clientes.",
            )
        if route == "product":
            source = current
            if not re.search(BRANDS, source):
                source = next(
                    (normalize(t) for t in reversed(user_texts) if re.search(BRANDS, normalize(t))),
                    current,
                )
            brand = re.search(r"\b(" + BRANDS + r")\s+([a-z0-9-]+)", source)
            query = brand[0] if brand else ""
            category = next(
                (
                    value
                    for key, value in {
                        "viol": "Violões",
                        "ukulele": "Ukuleles",
                        "guitarra": "Guitarras",
                        "baixo": "Baixos",
                        "bateria": "Baterias",
                        "teclado": "Teclados",
                    }.items()
                    if key in current
                ),
                None,
            )
            budget = re.search(r"ate\s*(?:r\$\s*)?([\d.,]+)", current)
            amount = None
            if budget:
                number = budget[1].rstrip(".,")
                amount = float(number.replace(".", "").replace(",", "."))
            return call(
                "search_products",
                query=query,
                category=category,
                max_price_brl=amount,
                only_available=not bool(brand),
                limit=5,
            )
        if route == "order":
            order = re.findall(r"pedido\s*#?\s*(\d+)", all_text)
            emails = re.findall(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", all_text)
            if order and emails:
                return call("get_order", order_id=int(order[-1]), customer_email=emails[-1])
            return call("search_policies", query="código de rastreamento", limit=2)
        if route == "return":
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", all_text)
            return call(
                "assess_return",
                reason="defect" if "defeito" in all_text else "regret",
                online=True if "online" in all_text else None,
                purchase_date=dates[-1] if dates and "defeito" in all_text else None,
                received_date=dates[-1] if dates and "recebi" in all_text else None,
                condition_confirmed=True if "sem uso" in all_text else None,
            )
        return call(
            "search_policies",
            query=current if route == "policy" else "escopo instrumentos",
            limit=3,
        )

    @staticmethod
    def _products(outputs: list[dict]) -> str:
        if len(outputs) > 1:
            quote = outputs[-1]
            if quote.get("eligible") is not True:
                return quote["message"] + " Fonte: manual, seção 3.1."
            product = quote["product"]
            payment = {
                "pix": "PIX",
                "credit": "cartão de crédito",
                "debit": "débito",
                "boleto": "boleto",
            }[quote["payment_method"]]
            result = f"{product['name']}: {quote['total']} no {payment}."
            if product["discount_percent"]:
                result += (
                    f" De {product['list_price']} por {product['price']} "
                    f"({product['discount_percent']}% de desconto). "
                    "PIX não acumula desconto sobre a promoção."
                )
            if quote["installments"] > 1:
                result += " Parcelas sem juros: " + ", ".join(quote["installment_amounts"]) + "."
            return (
                result + " Frete não incluído. Fontes: products.csv, promotions.csv e manual 3/6.2."
            )
        products = outputs[0].get("products", [])
        if not products:
            return (
                "Não encontrei produtos com esses filtros no snapshot local. Quer ampliar a busca?"
            )
        lines = []
        for p in products:
            price = (
                f"de {p['list_price']} por {p['price']} ({p['discount_percent']}% de desconto)"
                if p["discount_percent"]
                else p["price"]
            )
            availability = (
                f"{p['stock_quantity']} em estoque"
                if p["available"]
                else {
                    "discontinued": "descontinuado",
                    "coming_soon": "lançamento futuro",
                }.get(p["status"], "temporariamente esgotado")
            )
            lines.append(f"- {p['name']}: {price}; {availability}.")
        if outputs[0]["has_more"]:
            lines.append("Há mais opções com esses filtros. Posso refinar a busca.")
        return (
            "Consultei o catálogo local:\n"
            + "\n".join(lines)
            + ("\nFonte: products.csv + categories.csv + promotions.csv.")
        )
