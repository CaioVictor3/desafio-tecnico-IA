"""Cálculos verificáveis das regras do manual fornecido, sem decisões jurídicas."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from emporio.catalog import Catalog, DataError
from emporio.policies import PolicyIndex
from emporio.text import brl


class Rules:
    def __init__(self, catalog: Catalog, policies: PolicyIndex):
        self.catalog = catalog
        self.policies = policies

    def check_version(self) -> None:
        self.policies.refresh()
        snapshot = json.loads(Path(__file__).with_name("rules_snapshot.json").read_text())
        if snapshot["policy_sha256"] != self.policies.sha256:
            raise DataError(
                "O manual mudou. Revise as regras em Python e rules_snapshot.json "
                "antes de emitir cálculos de pagamento ou devolução."
            )

    def quote(self, product_id: int, payment_method: str, installments: int) -> dict:
        self.check_version()
        product = self.catalog.product(product_id)
        if not product:
            return {"error": "product_not_found"}
        if not product["available"]:
            return {
                "error": "unavailable",
                "product": product,
                "message": "Produto sem disponibilidade para venda. Consulte alternativas.",
            }
        total = product["price_cents"]
        pix_discount = payment_method == "pix" and not product["discount_percent"]
        if pix_discount:
            total = int(
                (Decimal(total) * Decimal("0.95")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )
        if payment_method != "credit" and installments != 1:
            return {"error": "invalid_installments", "message": "Só crédito permite parcelas."}
        result = {
            "product": product,
            "payment_method": payment_method,
            "total_cents": total,
            "total": brl(total),
            "installments": installments,
            "pix_discount_applied": bool(pix_discount),
            "promotion_and_pix_stack": False,
            "shipping_included": False,
            "policy_sources": self.policies.source(["3", "3.1", "6.2"]),
        }
        if payment_method == "credit" and installments > 1:
            # Ambiguidade de R$ 50: não recusar nem prometer os casos que dependem da interpretação.
            minimum = 0 if installments <= 3 else 8000 if installments <= 6 else 10000
            if total // installments < 5000 and installments <= 3:
                return {
                    **result,
                    "eligible": None,
                    "message": "A regra abaixo de R$ 50,00 é "
                    "ambígua. Confirme o parcelamento com a equipe antes de fechar a compra.",
                }
            if total // installments < minimum:
                return {
                    **result,
                    "eligible": False,
                    "minimum_installment": brl(minimum),
                    "message": "O valor por parcela fica abaixo do mínimo desta faixa.",
                }
        quotient, remainder = divmod(total, installments)
        # Distribui os centavos, garantindo que a soma das parcelas seja exatamente o total.
        amounts = [quotient + (i < remainder) for i in range(installments)]
        return {
            **result,
            "eligible": True,
            "installment_amounts": [brl(a) for a in amounts],
            "installment_amounts_cents": amounts,
            "message": "Condição simulada no snapshot local, sujeita à confirmação da loja.",
        }

    def assess_return(
        self,
        reason: str,
        online: bool | None,
        purchase_date: str | None,
        received_date: str | None,
        condition_confirmed: bool | None,
        today: date,
    ) -> dict:
        self.check_version()
        section = {"regret": "4.1", "defect": "4.2", "preference": "4.3"}[reason]
        result = {
            "reason": reason,
            "today": today.isoformat(),
            "policy_sources": self.policies.source([section, "4.4", "8.1"]),
            "automatic_approval": False,
            "message": "Orientação conforme o manual fornecido; a equipe confirma o caso. "
            "Nenhuma devolução ou reembolso foi registrado.",
        }
        if reason == "regret" and online is not True:
            return {
                **result,
                "status": "needs_information" if online is None else "needs_review",
                "question": "A compra foi feita online? A seção 4.1 trata de compras online.",
            }
        if reason == "preference":
            return {
                **result,
                "status": "needs_review",
                "question": "O manual prevê até 7 dias, "
                "mas não explicita o marco inicial nesta seção. A equipe precisa confirmar "
                "a data, o estado do produto e o estoque do modelo desejado.",
            }
        anchor = purchase_date if reason == "defect" else received_date
        if not anchor:
            question = (
                "Qual foi a data da compra?"
                if reason == "defect"
                else (
                    "Em que data você recebeu o produto? "
                    "A previsão de entrega não substitui essa data."
                )
            )
            return {**result, "status": "needs_information", "question": question}
        start = date.fromisoformat(anchor)
        if start > today:
            return {
                **result,
                "status": "needs_information",
                "question": "Essa data está no futuro. Pode confirmar a data correta?",
            }
        deadline = start + timedelta(days=30 if reason == "defect" else 7)
        within = today <= deadline
        return {
            **result,
            "status": "within_window" if within else "needs_review",
            "elapsed_days": (today - start).days,
            "deadline": deadline.isoformat(),
            "within_window": within,
            "condition_confirmed": condition_confirmed,
            "next_step": (
                "Confirmar embalagem original, ausência de uso, acessórios/manuais e exceções "
                "com a equipe; reembolso na forma original em até 10 dias úteis e frete pela loja."
                if reason == "regret"
                else "Confirmar defeito de fabricação com a equipe. "
                "Após 30 dias, consultar garantia "
                "do fabricante; a seção 8.1 também prevê 90 dias desde o recebimento."
            ),
        }
