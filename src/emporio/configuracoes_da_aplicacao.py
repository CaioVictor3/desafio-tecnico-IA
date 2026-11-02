from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    state_dir: Path
    model: str
    api_key: str
    max_rounds: int

    @classmethod
    def load(cls, data_dir: Path | None = None) -> Settings:
        # Execução a partir do checkout editable ou de uma instalação com data/ no cwd.
        checkout = Path(__file__).resolve().parents[2]
        root = Path.cwd() if (Path.cwd() / "data").is_dir() else checkout
        load_dotenv(root / ".env", override=False)

        def resolve(name: str, default: str) -> Path:
            path = Path(os.getenv(name, default)).expanduser()
            return path if path.is_absolute() else root / path

        rounds = int(os.getenv("EMPORIO_MAX_ROUNDS", "6"))
        if not 1 <= rounds <= 12:
            raise ValueError("EMPORIO_MAX_ROUNDS deve estar entre 1 e 12.")
        return cls(
            data_dir=data_dir.resolve() if data_dir else resolve("EMPORIO_DATA_DIR", "data"),
            state_dir=resolve("EMPORIO_STATE_DIR", ".state"),
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            max_rounds=rounds,
        )
