"""CSV -> SQLite em memória. Apenas consultas parametrizadas ficam expostas ao agente."""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import date
from pathlib import Path

from emporio.text import brl, cents, normalize, tokens

TABLES = ("categories", "products", "customers", "orders", "order_items", "promotions")
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE categories(id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL);
CREATE TABLE products(
 id INTEGER PRIMARY KEY, price INTEGER NOT NULL CHECK(price>=0), name TEXT NOT NULL,
 category_id INTEGER NOT NULL REFERENCES categories(id), description TEXT NOT NULL,
 stock INTEGER NOT NULL CHECK(stock>=0), status TEXT NOT NULL
 CHECK(status IN ('active','discontinued','coming_soon')), specs TEXT NOT NULL, created_at TEXT
);
CREATE TABLE customers(id INTEGER PRIMARY KEY, email TEXT NOT NULL);
CREATE TABLE orders(
 id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id),
 order_date TEXT NOT NULL, status TEXT NOT NULL, total INTEGER NOT NULL CHECK(total>=0),
 payment_method TEXT NOT NULL, tracking_code TEXT, estimated_delivery TEXT, notes TEXT
);
CREATE TABLE order_items(
 order_id INTEGER NOT NULL REFERENCES orders(id), quantity INTEGER NOT NULL CHECK(quantity>0),
 product_id INTEGER NOT NULL REFERENCES products(id), PRIMARY KEY(order_id,product_id)
);
CREATE TABLE promotions(
 id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id),
 discount INTEGER NOT NULL CHECK(discount BETWEEN 0 AND 100), description TEXT NOT NULL,
 active INTEGER NOT NULL CHECK(active IN (0,1))
);
"""


class DataError(ValueError):
    """Fonte ausente, ambígua ou inconsistente; não servir valores antigos silenciosamente."""


class Catalog:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._signature: tuple = ()
        self._db: sqlite3.Connection | None = None
        self.refresh()

    def _sources(self) -> dict[str, Path]:
        result = {}
        for name in TABLES:
            matches = sorted(self.data_dir.glob(f"*{name}.csv"))
            if len(matches) != 1:
                raise DataError(f"Esperado exatamente um CSV de {name} em {self.data_dir}.")
            result[name] = matches[0]
        return result

    def refresh(self) -> None:
        sources = self._sources()
        signature = tuple(
            (str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in sources.values()
        )
        if signature == self._signature:
            return
        new_db = sqlite3.connect(":memory:")
        new_db.row_factory = sqlite3.Row
        new_db.create_function("normalize", 1, normalize, deterministic=True)
        try:
            new_db.executescript(SCHEMA)
            for table, path in sources.items():
                with path.open(encoding="utf-8-sig", newline="") as source:
                    for row in csv.DictReader(source):
                        self._insert(new_db, table, row)
            new_db.commit()
            new_db.execute("PRAGMA query_only=ON")
        except (KeyError, ValueError, sqlite3.Error, csv.Error) as exc:
            new_db.close()
            raise DataError("CSV inválido: confira cabeçalhos, tipos, IDs e referências.") from exc
        if self._db:
            self._db.close()
        self._db, self._signature = new_db, signature

    @staticmethod
    def _insert(db: sqlite3.Connection, table: str, r: dict) -> None:
        # Os identificadores SQL são constantes internas, nunca texto vindo do modelo.
        match table:
            case "categories":
                values = (int(r["category_id"]), r["name"], r["description"])
            case "products":
                specs = json.loads(r["specs"])
                if not isinstance(specs, dict):
                    raise ValueError("specs deve ser um objeto JSON.")
                date.fromisoformat(r["created_at"])
                values = (
                    int(r["product_id"]),
                    cents(r["price_brl"]),
                    r["name"],
                    int(r["category_id"]),
                    r["description"],
                    int(r["stock_quantity"]),
                    r["status"],
                    json.dumps(specs, ensure_ascii=False),
                    r["created_at"],
                )
            case "customers":
                values = (int(r["customer_id"]), r["email"].strip().casefold())
            case "orders":
                date.fromisoformat(r["order_date"])
                if r["estimated_delivery"]:
                    date.fromisoformat(r["estimated_delivery"])
                if r["status"] not in {"pending", "confirmed", "shipped", "delivered", "cancelled"}:
                    raise ValueError("Status de pedido inválido.")
                values = (
                    int(r["order_id"]),
                    int(r["customer_id"]),
                    r["order_date"],
                    r["status"],
                    cents(r["total_brl"]),
                    r["payment_method"],
                    r["tracking_code"] or None,
                    r["estimated_delivery"] or None,
                    r["notes"] or None,
                )
            case "order_items":
                values = (int(r["order_id"]), int(r["quantity"]), int(r["product_id"]))
            case "promotions":
                values = (
                    int(r["promotion_id"]),
                    int(r["product_id"]),
                    int(r["discount_percent"]),
                    r["description"],
                    int(r["is_active"]),
                )
            case _:
                raise ValueError("Tabela não permitida.")
        placeholders = ",".join("?" for _ in values)
        db.execute(f"INSERT INTO {table} VALUES ({placeholders})", values)

    @property
    def db(self) -> sqlite3.Connection:
        self.refresh()
        assert self._db is not None
        return self._db

    def counts(self) -> dict[str, int]:
        return {
            name: self.db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in TABLES
        }

    def _product(self, r: sqlite3.Row) -> dict:
        promo = self.db.execute(
            "SELECT discount,description FROM promotions WHERE product_id=? AND active=1 "
            "ORDER BY discount DESC,id LIMIT 1",
            (r["id"],),
        ).fetchone()
        # Promoções só são oferecidas para produtos comercializáveis em estoque.
        available = r["status"] == "active" and r["stock"] > 0
        discount = promo["discount"] if promo and available else 0
        from decimal import ROUND_HALF_UP, Decimal

        current = int(
            (Decimal(r["price"]) * (100 - discount) / 100).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        return {
            "product_id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "description": r["description"],
            "specs": json.loads(r["specs"]),
            "status": r["status"],
            "stock_quantity": r["stock"],
            "available": available,
            "list_price_cents": r["price"],
            "list_price": brl(r["price"]),
            "price_cents": current,
            "price": brl(current),
            "discount_percent": discount,
            "promotion": promo["description"] if discount else None,
            "source": "products.csv + categories.csv + promotions.csv (snapshot local atualizado)",
        }

    def product(self, product_id: int) -> dict | None:
        r = self.db.execute(
            "SELECT p.*,c.name AS category FROM products p JOIN categories c ON c.id=p.category_id "
            "WHERE p.id=?",
            (product_id,),
        ).fetchone()
        return self._product(r) if r else None

    def search(
        self,
        query: str = "",
        category: str | None = None,
        max_price_cents: int | None = None,
        only_available: bool = True,
        limit: int = 5,
    ) -> dict:
        words = tokens(query)
        clauses, args = [], []
        for word in words:
            # instr evita que % e _ enviados pelo cliente virem curingas SQL.
            clauses.append(
                "instr(normalize(p.name || ' ' || c.name || ' ' || p.description "
                "|| ' ' || p.specs),?)>0"
            )
            args.append(word)
        if category:
            clauses.append("instr(normalize(c.name),?)>0")
            args.append(normalize(category))
        if only_available:
            clauses.append("p.status='active' AND p.stock>0")
        where = " AND ".join(clauses) or "1=1"
        rows = self.db.execute(
            "SELECT p.*,c.name AS category FROM products p JOIN categories c ON c.id=p.category_id "
            f"WHERE {where}",
            args,
        ).fetchall()
        products = [self._product(r) for r in rows]
        if max_price_cents is not None:
            products = [p for p in products if p["price_cents"] <= max_price_cents]
        products.sort(key=lambda p: (p["price_cents"], p["product_id"]))
        return {
            "products": products[:limit],
            "total_found": len(products),
            "has_more": len(products) > limit,
        }

    def order(self, order_id: int, email: str) -> dict:
        # Mesma resposta para ID inexistente e e-mail divergente evita enumeração simples.
        row = self.db.execute(
            "SELECT o.* FROM orders o JOIN customers c ON c.id=o.customer_id "
            "WHERE o.id=? AND c.email=?",
            (order_id, email.strip().casefold()),
        ).fetchone()
        if not row:
            return {
                "error": "order_not_verified",
                "message": "Não consegui validar esse pedido com o e-mail informado.",
            }
        items = self.db.execute(
            "SELECT i.quantity,p.name FROM order_items i JOIN products p ON p.id=i.product_id "
            "WHERE i.order_id=? ORDER BY p.id",
            (order_id,),
        ).fetchall()
        return {
            "order_id": row["id"],
            "order_date": row["order_date"],
            "status": row["status"],
            "total": brl(row["total"]),
            "payment_method": row["payment_method"],
            "tracking_code": row["tracking_code"],
            "estimated_delivery": row["estimated_delivery"],
            "notes": row["notes"],
            "items": [dict(r) for r in items],
            "source": "orders.csv + order_items.csv (snapshot local; sem rastreio externo)",
            "warning": "Previsão não confirma data de entrega; não existe delivered_at na base.",
        }

    def close(self) -> None:
        if self._db:
            self._db.close()
