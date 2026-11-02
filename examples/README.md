# Conversas com a OpenAI

As respostas de demonstração foram removidas. Esta pasta recebe apenas conversas
geradas por chamadas reais à OpenAI, com as ferramentas que consultam os materiais
fornecidos no teste técnico.

Com `OPENAI_API_KEY` configurada e créditos disponíveis, execute na raiz:

```bash
uv run python scripts/avaliar_atendimento_com_modelo_real.py --output-dir examples
```

O comando faz chamadas reais, que podem gerar cobrança. Se a API falhar antes de
consultar os dados, a execução para e informa o erro, sem fabricar uma resposta.
Revise as conversas geradas antes de publicar ou entregar o repositório.
