"""Smoke evaluation opt-in: faz chamadas reais à API configurada e pode gerar custo."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from emporio.agent import Agent
from emporio.catalog import Catalog
from emporio.config import Settings
from emporio.history import History
from emporio.policies import PolicyIndex
from emporio.provider import OpenAIProvider
from emporio.tools import Toolbox

SCENARIOS = [
    ("catalogo", "Quais violões disponíveis até R$ 1000?", {"search_products"}, None),
    ("endereco", "Qual o endereço da loja?", {"search_policies"}, "3200"),
    ("promocao", "Quanto custa o Ohana CK-20 no PIX?", {"search_products", "get_quote"}, "439"),
    (
        "pedido",
        "Meu pedido é 8 e meu e-mail é anacarol.ferreira@coldmail.com. Qual é o status?",
        {"get_order"},
        "BRJL5544332BR",
    ),
    (
        "devolucao",
        "Me arrependi da compra online. Ainda não informei quando recebi. Como faço para devolver?",
        {"assess_return"},
        None,
    ),
]


def main():
    settings = Settings.load()
    if not settings.api_key:
        raise SystemExit("Configure OPENAI_API_KEY no .env para avaliar o LLM real.")
    catalog = Catalog(settings.data_dir)
    policies = PolicyIndex(next(settings.data_dir.glob("*.pdf")))
    today = datetime.now(ZoneInfo("America/Campo_Grande")).date()
    provider = OpenAIProvider(settings.api_key, settings.model)
    target = settings.state_dir / "live"
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    results = []
    for name, message, expected, substring in SCENARIOS:
        history = History()
        answer = Agent(
            provider, Toolbox(catalog, policies, today), history, settings.max_rounds
        ).reply(message)
        used = {t["tool"] for t in answer.trace if t["ok"]}
        ok = expected <= used and (substring is None or substring in answer.text)
        path = target / f"{name}.md"
        path.write_text(
            f"# {name} · LLM {settings.model}\n\nData: {today}\n\n"
            f"Cliente: {message}\n\nMel: {answer.text}\n\n"
            f"Ferramentas: {', '.join(sorted(used))}\n",
            encoding="utf-8",
        )
        path.chmod(0o600)
        results.append({"scenario": name, "passed": ok, "tools": sorted(used)})
        history.close()
        print(f"{name}: {'PASS' if ok else 'REVIEW'}")
    catalog.close()
    report = target / "results.json"
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report.chmod(0o600)
    print(f"Transcrições locais: {target}")
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
