"""Retrieval lexical BM25, com seções e páginas do PDF como evidência."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from emporio.catalog import DataError
from emporio.text import tokens

STOP = set("a o as os de da do das dos e em um uma para por com que qual quais como no na "
           "nos nas eu meu minha me posso voces sobre ate loja".split())
ALIASES = {
    "abre": "horario", "aberto": "horario", "fecha": "horario", "funciona": "funcionamento",
    "horarios": "horario", "pagamentos": "pagamento", "parcelas": "parcelamento",
    "parcelar": "parcelamento", "devolver": "devolucao", "devolucoes": "devolucao",
    "arrependi": "arrependimento", "trocar": "troca", "trocas": "troca",
    "defeitos": "defeito", "endereco": "endereco", "onde": "endereco",
    "localizacao": "endereco", "contato": "telefone", "prazo": "prazo",
    "entrega": "entrega", "entregas": "entrega", "descontos": "desconto",
    "promocoes": "promocao", "dados": "privacidade", "lgpd": "privacidade",
    "cordas": "acessorios", "cabos": "acessorios", "palhetas": "acessorios",
    "pedais": "acessorios", "amplificador": "acessorios", "cases": "acessorios",
}


def terms(text: str) -> list[str]:
    return [ALIASES.get(t, t) for t in tokens(text) if t not in STOP]


@dataclass
class Section:
    section: str
    title: str
    text: str
    pages: list[int]


class PolicyIndex:
    def __init__(self, path: Path):
        self.path = path
        self.sha256 = ""
        self.sections: list[Section] = []
        self.refresh()

    def refresh(self) -> None:
        if not self.path.is_file():
            raise DataError("Manual de políticas não encontrado em data/.")
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        if digest == self.sha256:
            return
        sections: list[Section] = []
        current = Section("capa", "Identificação e contato", "", [])
        with pdfplumber.open(self.path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                for line in (page.extract_text() or "").splitlines():
                    if (line.startswith("Empório da Música Manual")
                            or re.match(r"^Página\s+\d+", line)):
                        continue
                    heading = re.match(r"^(\d+(?:\.\d+)?)\.?\s+([A-ZÀ-Ú].+)$", line)
                    if heading:
                        if current.text.strip():
                            sections.append(current)
                        current = Section(heading[1], heading[2], "", [])
                    current.text += line + "\n"
                    if page_num not in current.pages:
                        current.pages.append(page_num)
        if current.text.strip():
            sections.append(current)
        if len(sections) < 10:
            raise DataError("Extração do manual insuficiente; é necessária revisão do PDF.")
        self.sections, self.sha256 = sections, digest

    def source(self, section_ids: list[str]) -> list[dict]:
        self.refresh()
        return [self._serialize(s) for s in self.sections if s.section in section_ids]

    def _serialize(self, section: Section) -> dict:
        return {"source": self.path.name, "section": section.section, "title": section.title,
                "pages": section.pages, "text": section.text.strip()}

    def search(self, query: str, limit: int = 4) -> dict:
        self.refresh()
        query_terms = set(terms(query))
        bags = [Counter(terms(s.title + " " + s.text)) for s in self.sections]
        average = sum(sum(b.values()) for b in bags) / len(bags)
        scores = []
        for s, bag in zip(self.sections, bags, strict=True):
            score = 0.0
            for term in query_terms:
                frequency = bag[term]
                if not frequency:
                    continue
                document_count = sum(term in b for b in bags)
                idf = math.log(1 + (len(bags) - document_count + 0.5) / (document_count + 0.5))
                score += idf * frequency * 2.5 / (
                    frequency + 1.5 * (0.25 + 0.75 * sum(bag.values()) / average))
            if score > 0:
                scores.append((score, s))
        scores.sort(key=lambda pair: pair[0], reverse=True)
        return {"matches": [self._serialize(s) for _, s in scores[:limit]],
                "found": bool(scores),
                "guidance": "Use só evidências relevantes; ausência não autoriza inventar uma regra.",
                "ambiguities": [
                    "Contatos divergem: seção 1.2/capa (67) 3341-4444; seção 7 (67) 3321-4500. "
                    "E-mail da capa sem acento diverge da seção 1.2. Informe a divergência se relevante.",
                    "Parcelamento: priorizar seção 3.1 sobre a tabela geral da seção 3; "
                    "a exceção abaixo de R$ 50,00 não define claramente se trata da compra ou parcela.",
                    "Frete local: o manual omite o caso de exatamente R$ 500,00. Consultar equipe.",
                    "Restrições de troca no manual não são uma decisão jurídica nem negativa automática.",
                ]}

