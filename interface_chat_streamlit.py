"""Execute: uv run streamlit run interface_chat_streamlit.py."""

from __future__ import annotations

import streamlit as st

from emporio.configuracoes_da_aplicacao import Settings
from emporio.repositorio_catalogo_e_pedidos import DataError
from emporio.servico_de_conversa_da_interface import responder_mensagem


def exibir_mensagem(texto: str) -> None:
    # O cifrão de BRL deve aparecer como moeda, sem iniciar uma expressão LaTeX.
    st.markdown(texto.replace("R$", r"R\$"))


def limpar_conversa() -> None:
    st.session_state["mensagens_exibidas"] = []
    st.session_state["historico_do_agente"] = []


def main() -> None:
    st.set_page_config(page_title="Empório da Música · Chat", page_icon="🎵", layout="centered")
    try:
        configuracoes = Settings.load()
    except (ValueError, OSError):
        st.error("Não consegui carregar as configurações. Confira o arquivo .env do projeto.")
        st.stop()

    st.session_state.setdefault("mensagens_exibidas", [])
    st.session_state.setdefault("historico_do_agente", [])
    if st.session_state.get("versao_do_atendimento") != "openai_csv_exclusivo":
        limpar_conversa()
        st.session_state["versao_do_atendimento"] = "openai_csv_exclusivo"

    with st.sidebar:
        st.subheader("Seu atendimento")
        st.button("Nova conversa", on_click=limpar_conversa, width="stretch")
        if not configuracoes.api_key:
            st.warning("Configure OPENAI_API_KEY no .env para conversar com a IA.")
        else:
            st.caption("Chave da API configurada para o atendimento com IA.")
        st.caption("A conversa fica nesta sessão. Nova conversa apaga o contexto atual.")

    st.title("Empório da Música")
    st.caption("Sua música começa aqui.")
    with st.chat_message("assistant", avatar="🎵"):
        st.markdown(
            "Oi! Sou a Mel, assistente virtual da Empório da Música. "
            "Posso ajudar com instrumentos, preços, disponibilidade e pedidos."
        )

    for mensagem in st.session_state["mensagens_exibidas"]:
        avatar = "🎵" if mensagem["role"] == "assistant" else None
        with st.chat_message(mensagem["role"], avatar=avatar):
            exibir_mensagem(mensagem["content"])

    bloqueado = not configuracoes.api_key
    pergunta = st.chat_input("Escreva sua pergunta para a Mel…", max_chars=4000, disabled=bloqueado)
    if not pergunta or not pergunta.strip():
        return

    with st.chat_message("user"):
        exibir_mensagem(pergunta)
    with st.chat_message("assistant", avatar="🎵"):
        with st.spinner("A Mel está consultando as informações da loja…"):
            try:
                resposta, historico = responder_mensagem(
                    pergunta,
                    st.session_state["historico_do_agente"],
                    configuracoes,
                )
                texto_da_resposta = resposta.text
                st.session_state["historico_do_agente"] = historico
            except (DataError, ValueError, OSError):
                texto_da_resposta = (
                    "Não consegui consultar as informações agora. "
                    "Tente novamente em alguns instantes ou fale com a equipe da loja."
                )
        exibir_mensagem(texto_da_resposta)
    st.session_state["mensagens_exibidas"] = (
        st.session_state["mensagens_exibidas"]
        + [
            {"role": "user", "content": pergunta},
            {"role": "assistant", "content": texto_da_resposta},
        ]
    )[-40:]


if __name__ == "__main__":
    main()
