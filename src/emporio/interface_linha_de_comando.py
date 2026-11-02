from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from emporio.agente_de_atendimento import Agent
from emporio.busca_politicas_da_loja import PolicyIndex
from emporio.configuracoes_da_aplicacao import Settings
from emporio.ferramentas_de_consulta import Toolbox
from emporio.historico_de_conversas import History
from emporio.integracao_modelo_openai import OpenAIProvider
from emporio.provedor_de_demonstracao import DemoProvider
from emporio.repositorio_catalogo_e_pedidos import Catalog, DataError


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Empório da Música · Sua música começa aqui.")
    result.add_argument("--data-dir", type=Path, help="Pasta com os seis CSVs e o manual PDF.")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="Validar fontes sem fazer chamadas de API.")
    chat = commands.add_parser("chat", help="Conversar com a Mel.")
    chat.add_argument("--provider", choices=["openai", "demo"], default="openai")
    chat.add_argument("--message", help="Executar uma única mensagem e sair.")
    chat.add_argument(
        "--session", help="Optar por histórico persistente em SQLite, por identificador."
    )
    chat.add_argument(
        "--trace", action="store_true", help="Mostrar ferramentas e latência no stderr."
    )
    chat.add_argument("--today", type=date.fromisoformat, help="Fixar data, só na demonstração.")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    catalog, history = None, None
    try:
        settings = Settings.load(args.data_dir)
        catalog = Catalog(settings.data_dir)
        manuals = list(settings.data_dir.glob("*.pdf"))
        if len(manuals) != 1:
            raise DataError("Esperado exatamente um manual PDF na pasta data/.")
        policies = PolicyIndex(manuals[0])
        today = datetime.now(ZoneInfo("America/Campo_Grande")).date()
        toolbox = Toolbox(catalog, policies, today)
        if args.command == "check":
            toolbox.rules.check_version()
            print(
                json.dumps(
                    {
                        "ok": True,
                        "tables": catalog.counts(),
                        "policy_sections": len(policies.sections),
                        "policy_sha256": policies.sha256,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.today:
            if args.provider != "demo":
                raise ValueError("--today é permitido apenas com --provider demo.")
            toolbox.today = args.today
        provider = (
            DemoProvider()
            if args.provider == "demo"
            else OpenAIProvider(settings.api_key, settings.model)
        )
        history = History(
            settings.state_dir / "history.sqlite3" if args.session else None,
            args.session or "temporary",
        )
        agent = Agent(provider, toolbox, history, settings.max_rounds)
        if args.provider == "demo":
            print(
                "[DEMO determinística, sem LLM/API; vocabulário limitado. "
                "Use OpenAI para o agente.]",
                file=sys.stderr,
            )
        if args.session:
            print(
                f"[Histórico local persistente: sessão {args.session}. "
                "/limpar remove esta sessão.]",
                file=sys.stderr,
            )

        def respond(message: str) -> None:
            answer = agent.reply(message)
            print(answer.text)
            if args.trace:
                print(json.dumps(answer.trace, ensure_ascii=False), file=sys.stderr)

        if args.message is not None:
            respond(args.message)
            return 0
        print("Oi! Sou a Mel, assistente virtual da Empório da Música. Como posso ajudar?")
        print("Comandos: /sair · /limpar (apagar histórico desta sessão)")
        while True:
            try:
                message = input("\nVocê: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nAté a próxima! Sua música começa aqui.")
                break
            if message == "/sair":
                break
            if message == "/limpar":
                history.clear()
                print("Histórico desta sessão removido.")
            elif message:
                respond(message)
        return 0
    except (DataError, ValueError, OSError) as exc:
        print(f"Não foi possível iniciar: {exc}", file=sys.stderr)
        return 2
    finally:
        if catalog:
            catalog.close()
        if history:
            history.close()


if __name__ == "__main__":
    raise SystemExit(main())
