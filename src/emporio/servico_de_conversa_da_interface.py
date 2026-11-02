"""Conecta a interface ao agente sem compartilhar conexões ou dados entre sessões."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from emporio.agente_de_atendimento import Agent, Answer
from emporio.busca_politicas_da_loja import PolicyIndex
from emporio.configuracoes_da_aplicacao import Settings
from emporio.ferramentas_de_consulta import Toolbox
from emporio.historico_de_conversas import History
from emporio.integracao_modelo_openai import OpenAIProvider
from emporio.provedor_de_demonstracao import DemoProvider
from emporio.repositorio_catalogo_e_pedidos import Catalog, DataError


def responder_mensagem(
    mensagem: str,
    modo: str,
    historico_anterior: list[dict],
    configuracoes: Settings,
) -> tuple[Answer, list[dict]]:
    """Cada execução tem conexões próprias; só texto serializável fica no Streamlit."""
    if modo not in {"openai", "demo"}:
        raise ValueError("Modo de atendimento inválido.")
    catalogo, historico, provedor = None, None, None
    try:
        catalogo = Catalog(configuracoes.data_dir)
        manuais = list(configuracoes.data_dir.glob("*.pdf"))
        if len(manuais) != 1:
            raise DataError("Esperado exatamente um manual PDF na pasta data/.")
        politicas = PolicyIndex(manuais[0])
        hoje = datetime.now(ZoneInfo("America/Campo_Grande")).date()
        ferramentas = Toolbox(catalogo, politicas, hoje)
        historico = History()
        for indice in range(0, len(historico_anterior) - 1, 2):
            cliente, assistente = historico_anterior[indice : indice + 2]
            historico.save_turn(cliente["content"], assistente["content"])
        provedor = (
            DemoProvider()
            if modo == "demo"
            else OpenAIProvider(configuracoes.api_key, configuracoes.model)
        )
        agente = Agent(provedor, ferramentas, historico, configuracoes.max_rounds)
        resposta = agente.reply(mensagem)
        return resposta, historico.load()
    finally:
        if catalogo:
            catalogo.close()
        if historico:
            historico.close()
        if isinstance(provedor, OpenAIProvider):
            provedor.client.close()
