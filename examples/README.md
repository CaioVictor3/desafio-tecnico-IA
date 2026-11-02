# Conversas com OpenAI e consultas aos CSVs

Esta pasta recebe apenas conversas geradas pela OpenAI real com dados dos seis CSVs.
O atendimento não consulta PDF nem utiliza regras derivadas de documentos externos.

Com chave e créditos disponíveis, execute na raiz:

```bash
uv run python scripts/avaliar_atendimento_com_modelo_real.py --output-dir examples
```

Os cenários cobrem catálogo, preço, promoção ativa, identificação de pedido e uma
pergunta cuja informação não existe nos CSVs. O comando pode gerar cobrança.
Se a API falhar, a execução para sem fabricar uma conversa. Revise as respostas
antes de publicar ou entregar o repositório.
