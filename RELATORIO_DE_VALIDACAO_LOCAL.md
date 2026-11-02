# Validação da versão exclusiva OpenAI

Execução local em 02/11/2026, Python 3.12.5, macOS.

| Verificação | Resultado |
| --- | --- |
| `uv run pytest -q` | 60 testes locais aprovados |
| `uv run emporio check` | Seis CSVs válidos, 29 seções de políticas |
| `uv run ruff check . tests/` | Sem erros |
| `uv run ruff format --check . tests/` | Arquivos formatados |
| Interface Streamlit | Sem seletor de provedor; perguntas bloqueadas sem chave |
| Falha da OpenAI | Erro apresentado sem resposta alternativa; sem retentativa automática |
| Teste real pelo terminal | API retornou `credit_balance_exhausted` |

A aplicação usa apenas o adaptador OpenAI. O provedor de demonstração, o gerador
de respostas programadas e as cinco conversas produzidas por ele foram removidos.
A transição da interface limpa o contexto da versão anterior na sessão do navegador.
Os materiais originais do teste técnico em `data/` foram preservados.

Os testes locais verificam consultas, cálculos, validações, histórico, contrato HTTP
do SDK e a interface. O transporte HTTP isolado existe apenas dentro de `tests/`,
que continua ignorado pelo Git e ausente de todos os commits publicáveis. A versão
instalada da aplicação não tem provedor de atendimento alternativo.

Uma pergunta real enviada pelo comando `emporio chat` chegou à OpenAI, que recusou
a solicitação por falta de créditos na organização vinculada à chave. Não houve
resposta de atendimento gerada nessa verificação; nenhuma resposta foi fabricada
para substituí-la. A chave e o corpo bruto do erro não foram registrados.

Para validar respostas do modelo e gerar as cinco conversas de entrega, regularize
o saldo da API e execute:

```bash
uv run python scripts/avaliar_atendimento_com_modelo_real.py --output-dir examples
```

O comando usa a API real e pode gerar cobrança. As conversas só são gravadas quando
o agente conclui uma resposta. As respostas ao cliente não citam fontes internas;
as consultas e os metadados de origem continuam disponíveis para o agente.

Não houve publicação no GitHub, envio de e-mail ou alteração do faturamento da
conta OpenAI. A matriz de CI Linux/Python 3.11 e 3.12 não foi executada remotamente.
