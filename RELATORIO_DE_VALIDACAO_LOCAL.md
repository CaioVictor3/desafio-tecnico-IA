# Validação da implementação

Execução local em 02/11/2026, Python 3.12.5, macOS.

| Verificação | Resultado |
| --- | --- |
| `uv run emporio check` | OK: seis CSVs válidos, 29 seções de políticas |
| `uv run pytest -q` | 52 testes locais aprovados, incluindo o chat Streamlit |
| `uv run ruff check .` | Sem erros |
| `uv run ruff format --check .` | Arquivos formatados |
| CLI em dois processos com a mesma sessão | Contexto e identificação do produto preservados |
| Streamlit AppTest | Pergunta/resposta, contexto, nova conversa, modos, isolamento e erro de fonte |
| Chat no navegador local | Pergunta e preço promocional exibidos em http://127.0.0.1:8501 |
| `scripts/gerar_conversas_de_exemplo.py` | Cinco conversas geradas com ferramentas reais no modo demo |

As fontes têm 65 produtos, 9 categorias, 50 clientes, 20 pedidos, 22 itens de pedidos
e 25 registros de promoção. Os arquivos fornecidos foram preservados.

O contrato HTTP da Responses API foi testado com o SDK OpenAI real e transporte
HTTP simulado, incluindo chamada de ferramenta, resultado e resposta final.
Os cenários de falha de autenticação, limite do provedor e erro de servidor também
foram simulados, sem rede.

A validação automatizada usa chave vazia, demonstração e HTTP simulado. Não foram
feitas chamadas reais de inferência nesta validação, nem medidos qualidade
linguística, custo ou latência de um LLM.
Os exemplos estão identificados como demonstrações determinísticas. O comando
optativo `uv run python scripts/avaliar_atendimento_com_modelo_real.py` permite avaliação com credencial
do avaliador e pode gerar cobrança.

A configuração de CI inclui Python 3.11 e 3.12 em Linux; essa matriz remota ainda
não foi executada. O repositório foi criado localmente, sem publicação no GitHub
e sem envio de e-mail.

Os arquivos de teste foram mantidos apenas na pasta local `tests/`, ignorados pelo
Git e removidos de todos os commits publicáveis. A CI não depende de testes ausentes.
Os módulos, scripts e exemplos têm nomes descritivos em português. Os materiais
originais em `data/` e o enunciado em PDF mantêm seus nomes e conteúdo.

