from __future__ import annotations

import re
import unicodedata
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def normalize(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in plain if not unicodedata.combining(c))


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize(text))


def cents(value: str | Decimal) -> int:
    try:
        number = Decimal(value)
        if not number.is_finite() or number < 0:
            raise ValueError("Valor monetário inválido.")
        return int((number * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except InvalidOperation as exc:
        raise ValueError("Valor monetário inválido.") from exc


def brl(value_cents: int) -> str:
    integer, fraction = divmod(value_cents, 100)
    return f"R$ {integer:,}".replace(",", ".") + f",{fraction:02d}"
