from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from emporio.agente_de_atendimento import Agent
from emporio.configuracoes_da_aplicacao import Settings
from emporio.ferramentas_de_consulta import Toolbox
from emporio.historico_de_conversas import History
from emporio.integracao_modelo_openai import OpenAIProvider
from emporio.repositorio_catalogo_e_pedidos import Catalog, DataError


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Empório da Música · Sua música começa aqui.")
    result.add_argument("--data-dir", type=Path, help="Pasta com os seis CSVs do desafio.")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="Validar fontes sem fazer chamadas de API.")
    chat = commands.add_parser("chat", help="Conversar com a Mel.")
    chat.add_argument("--message", help="Executar uma única mensagem e sair.")
    chat.add_argument(
        "--session", help="Optar por histórico persistente em SQLite, por identificador."
    )
    chat.add_argument(
        "--trace", action="store_true", help="Mostrar ferramentas e latência no stderr."
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    catalog, history, provider = None, None, None
    try:
        settings = Settings.load(args.data_dir)
        catalog = Catalog(settings.data_dir)
        today = datetime.now(ZoneInfo("America/Campo_Grande")).date()
        toolbox = Toolbox(catalog, today)
        if args.command == "check":
            print(
                json.dumps(
                    {
                        "ok": True,
                        "tables": catalog.counts(),
                        "consultation_sources": "csv_only",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        provider = OpenAIProvider(settings.api_key, settings.model)
        history = History(
            settings.state_dir / "history.sqlite3" if args.session else None,
            args.session or "temporary",
        )
        agent = Agent(provider, toolbox, history, settings.max_rounds)
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
        if provider:
            provider.client.close()


if __name__ == "__main__":
    raise SystemExit(main())
