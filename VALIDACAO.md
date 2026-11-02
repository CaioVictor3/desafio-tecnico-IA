# Validação da implementação

Execução local em 02/11/2026, Python 3.12.5, macOS.

| Verificação | Resultado |
| --- | --- |
| `uv run emporio check` | OK: seis CSVs válidos, 29 seções de políticas |
| `uv run pytest -q` | 47 testes aprovados |
| `uv run ruff check .` | Sem erros |
| `uv run ruff format --check .` | Arquivos formatados |
| CLI em dois processos com a mesma sessão | Contexto e identificação do produto preservados |
| `scripts/generate_examples.py` | Cinco conversas geradas com ferramentas reais no modo demo |

As fontes têm 65 produtos, 9 categorias, 50 clientes, 20 pedidos, 22 itens de pedidos
e 25 registros de promoção. Os arquivos fornecidos foram preservados.

O contrato HTTP da Responses API foi testado com o SDK OpenAI real e transporte
HTTP simulado, incluindo chamada de ferramenta, resultado e resposta final.
Os cenários de falha de autenticação, limite do provedor e erro de servidor também
foram simulados, sem rede.

Não havia `OPENAI_API_KEY` configurada no ambiente. Não foram feitas chamadas reais
de inferência, nem medidos qualidade linguística, custo ou latência de um LLM.
Os exemplos estão identificados como demonstrações determinísticas. O comando
optativo `uv run python scripts/evaluate_live.py` permite avaliação com credencial
do avaliador e pode gerar cobrança.

A configuração de CI inclui Python 3.11 e 3.12 em Linux; essa matriz remota ainda
não foi executada. O repositório foi criado localmente, sem publicação no GitHub
e sem envio de e-mail.

