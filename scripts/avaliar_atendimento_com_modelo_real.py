"""Smoke evaluation opt-in: faz chamadas reais à API configurada e pode gerar custo."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from emporio.agente_de_atendimento import Agent
from emporio.configuracoes_da_aplicacao import Settings
from emporio.ferramentas_de_consulta import Toolbox
from emporio.historico_de_conversas import History
from emporio.integracao_modelo_openai import OpenAIProvider
from emporio.repositorio_catalogo_e_pedidos import Catalog

SCENARIOS = [
    ("catalogo", "Quais violões disponíveis até R$ 1000?", {"search_products"}, None),
    ("preco", "Quanto custa o Takamine GD20?", {"search_products"}, "2.199"),
    (
        "promocao",
        "Quanto custa o Ohana CK-20 na promoção atual?",
        {"search_products", "get_quote"},
        "439",
    ),
    (
        "pedido",
        "Meu pedido é 8 e meu e-mail é anacarol.ferreira@coldmail.com. Qual é o status?",
        {"get_order"},
        "BRJL5544332BR",
    ),
    (
        "informacao_indisponivel",
        "Qual é o horário de funcionamento da loja?",
        {"get_available_information"},
        None,
    ),
]


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Gerar conversas usando apenas a OpenAI real.")
    parser.add_argument("--output-dir", type=Path, help="Pasta de saída; por padrão, .state/live/.")
    args = parser.parse_args(argv)
    settings = Settings.load()
    if not settings.api_key:
        raise SystemExit("Configure OPENAI_API_KEY no .env para avaliar o LLM real.")
    catalog = Catalog(settings.data_dir)
    today = datetime.now(ZoneInfo("America/Campo_Grande")).date()
    provider = OpenAIProvider(settings.api_key, settings.model)
    target = args.output_dir.resolve() if args.output_dir else settings.state_dir / "live"
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    results = []
    try:
        for name, message, expected, substring in SCENARIOS:
            history = History()
            try:
                answer = Agent(
                    provider, Toolbox(catalog, today), history, settings.max_rounds
                ).reply(message)
                conversa_concluida = bool(history.load())
            finally:
                history.close()
            used = {t["tool"] for t in answer.trace if t["ok"]}
            ok = expected <= used and (substring is None or substring in answer.text)
            results.append({"scenario": name, "passed": ok, "tools": sorted(used)})
            if not conversa_concluida:
                print(f"{name}: não foi possível gerar uma conversa: {answer.text}")
                break
            path = target / f"{name}.md"
            path.write_text(
                f"# {name} · LLM {settings.model}\n\nData: {today}\n\n"
                f"Cliente: {message}\n\nMel: {answer.text}\n",
                encoding="utf-8",
            )
            path.chmod(0o600)
            print(f"{name}: {'PASS' if ok else 'REVIEW'}")
    finally:
        catalog.close()
        provider.client.close()
    report = target / "results.json"
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report.chmod(0o600)
    print(f"Transcrições locais: {target}")
    return 0 if len(results) == len(SCENARIOS) and all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
