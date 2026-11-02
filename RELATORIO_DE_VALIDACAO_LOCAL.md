# Validação: OpenAI com consultas exclusivas aos CSVs

Execução local em 02/11/2026, Python 3.12.5, macOS.

| Verificação | Resultado |
| --- | --- |
| `uv run pytest -q` | 54 testes locais aprovados |
| `uv run emporio check` | Seis CSVs válidos; consultation_sources = csv_only |
| `uv run ruff check . tests/` | Sem erros |
| `uv run ruff format --check . tests/` | Arquivos formatados |
| Pasta de consulta contendo somente CSVs | Validação e atendimento pela interface aprovados |
| PDF inválido e JSON inválido na pasta de dados | Ignorados; validação dos CSVs continua funcionando |
| Cotação sem condições de pagamento | Apenas preço de tabela e promoção ativa dos CSVs |
| Promoções ativas simultâneas | Exige confirmação, sem inventar regra de acumulação |

Foram removidos o leitor/indexador do PDF, as ferramentas de políticas e devolução,
as regras comerciais extraídas do manual, o arquivo de versão dessas regras e a
dependência pdfplumber. Os PDFs originais foram preservados como materiais do teste,
mas não são abertos nem consultados pela aplicação.

Os 65 produtos, 9 categorias, 50 clientes, 20 pedidos, 22 itens e 25 promoções são
validados e consultados a partir dos CSVs. Valores de PIX, parcelamento, frete,
troca, devolução, garantia, endereço e horários não são inferidos de outras fontes.
A interface limpa uma vez o contexto da versão anterior ao migrar para CSVs.

O atendimento continua exclusivo da OpenAI. O transporte HTTP isolado existe
somente nos testes locais, que permanecem fora do Git e da distribuição. Não foi
feita nova chamada real à API nesta alteração. O último teste real de acesso
retornou credit_balance_exhausted; saldo e limites da conta não foram alterados.

As conversas de entrega devem ser geradas com a API real após regularizar o acesso:

```bash
uv run python scripts/avaliar_atendimento_com_modelo_real.py --output-dir examples
```

Os cenários cobrem catálogo, preço, promoção, pedido e informação não disponível.
As respostas ao cliente não citam a origem interna dos dados. Não houve publicação
no GitHub, envio de e-mail ou execução remota da matriz de CI.
