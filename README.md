# Empório da Música · Chat com OpenAI e consultas aos CSVs

Aplicação Python para atendimento da Empório da Música, com interface local em
Streamlit e agente baseado na OpenAI Responses API. **Somente os seis CSVs do
teste técnico são usados nas consultas.**

## Executar

Requisitos: Python 3.11+, internet e chave OpenAI com acesso ao modelo e créditos.
Execute na raiz do projeto:

```bash
uv sync --frozen --extra dev
cp .env.example .env
# Preencha OPENAI_API_KEY no .env; preserve um .env existente.
uv run emporio check
uv run streamlit run interface_chat_streamlit.py
```

Abra [o chat local](http://127.0.0.1:8501). Escreva a pergunta e pressione Enter.
**Nova conversa** limpa o contexto. O servidor escuta em `127.0.0.1` e é encerrado
com Ctrl+C. Se a porta 8501 já estiver ocupada pelo chat, use a instância aberta.
Sem `OPENAI_API_KEY`, o campo de pergunta fica bloqueado. Alterações na chave
exigem reiniciar o servidor. O modelo padrão é `gpt-5-mini`, configurável no `.env`.

Alternativa com pip:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
streamlit run interface_chat_streamlit.py
```

O terminal também permite conversar:

```bash
uv run emporio chat
uv run emporio chat --trace --message 'Quanto custa o Ohana CK-20?'
uv run emporio chat --session avaliacao
```

No terminal, `/sair` encerra e `/limpar` remove o histórico lógico da sessão.
Não há modo de demonstração nem respostas programadas para substituir a OpenAI.
Falhas de acesso à API são apresentadas sem produzir uma resposta alternativa.

## Informações disponíveis

| CSV | Uso |
| --- | --- |
| `products.csv` | Produtos, descrição, especificações, preço de tabela, estoque e status |
| `categories.csv` | Categorias e descrições |
| `promotions.csv` | Promoções identificadas como ativas e percentual de desconto |
| `orders.csv` | Dados do pedido, status, total histórico, pagamento, rastreamento e previsão |
| `order_items.csv` | Itens e quantidades de cada pedido |
| `customers.csv` | Verificação do e-mail do comprador, sem expor a lista de clientes |

Os arquivos mantêm o prefixo original `desafio_tecnico_ai_eng - `. A pasta pode
conter os PDFs originais, preservados como materiais do desafio; a aplicação não
os abre, indexa ou consulta. Também foram removidas as regras extraídas desses PDFs.

**Os CSVs não têm condições gerais de PIX, parcelamento, frete, troca, devolução,
garantia, endereço, contato ou horário da loja.** Para esses assuntos, o agente
pede confirmação com a equipe. Não aplica desconto adicional de PIX, juros,
parcelas mínimas ou prazos de devolução baseados em informações externas.

Exemplos de perguntas:

```text
Quais violões disponíveis custam até R$ 1000?
Quanto custa o Takamine GD20?
Qual é o preço promocional do Ohana CK-20?
Quais categorias de instrumentos vocês têm?
Qual o status do pedido 8?
```

Para pedidos, informe número e e-mail da compra. Uma previsão de entrega não
comprova recebimento. A forma de pagamento registrada em um pedido histórico não
estabelece condições para novas compras.

## Arquitetura e decisões

```text
Streamlit / CLI -> agente Python -> OpenAI Responses API
                         |                  |
                         +--- ferramentas --+
                                  |
                         SQLite em memória
                                  |
                       seis CSVs do desafio
```

O agente usa function calling com argumentos validados pelo Pydantic e consultas
SQL parametrizadas. O loop é implementado diretamente em Python, sem framework
de agentes. A OpenAI interpreta a pergunta, escolhe ferramentas e redige a resposta.
O código consulta dados e calcula o desconto explícito da promoção ativa.

| Ferramenta | Responsabilidade |
| --- | --- |
| `search_products` | Buscar por termos, categoria, orçamento e disponibilidade |
| `get_quote` | Consultar o preço e a promoção ativa de um produto |
| `get_order` | Consultar um pedido após verificar número e e-mail |
| `get_available_information` | Consultar categorias e indicar quais dados estão disponíveis |

O agente consulta informações a cada turno e não usa respostas anteriores como
fonte de fatos. **A resposta ao cliente não cita arquivos, tabelas ou fontes.**
A interface limpa o contexto anterior uma vez ao migrar para esta versão de CSVs.
Não há pesquisa na internet, leitura de documentos ou ferramenta de SQL livre.

As escolhas seguem a [documentação de function calling](https://developers.openai.com/api/docs/guides/function-calling).
O modelo é configurável; sua disponibilidade depende da conta do avaliador.
Não há alegação de benchmark de qualidade do modelo.

## Tratamento dos dados e limites

- Os CSVs são validados: tipos, IDs, referências, datas, estoque e especificações JSON.
  Erros interrompem a consulta sem servir valores antigos silenciosamente.
- Os dados são importados em SQLite em memória. Alterações de tamanho/data dos CSVs
  provocam recarga. Não existe integração com estoque ou transportadora em tempo real.
- Valores monetários usam centavos inteiros e Decimal. Uma única promoção ativa
  permite calcular o preço pelo percentual presente no CSV. Se há mais de uma,
  o agente pede confirmação do preço final, sem inventar regras de acumulação.
- A oferta exige `status=active` e estoque positivo. Produtos descontinuados ou de
  lançamento futuro não são apresentados como disponíveis para compra.
- Totais históricos de pedidos são preservados, sem recalcular com preços atuais.
- O modelo recebe instruções de escopo, consulta obrigatória, privacidade e tratamento
  de instruções maliciosas em mensagens/descrições. Isso exige avaliação contínua.
- Há até seis rodadas por mensagem e doze chamadas de ferramenta no total. O SDK
  usa timeout de 30 segundos por chamada e não faz retentativas automáticas.

O histórico web fica em memória na sessão do navegador, limitado a vinte interações.
As conexões são abertas e fechadas por pergunta, sem compartilhar SQLite entre threads.
Na CLI, `--session` opta por persistência em `.state/history.sqlite3`. `/limpar`
remove linhas lógicas, sem prometer apagar backups ou realizar limpeza forense.

Verificação por e-mail é apenas identificação do protótipo: produção exigiria
sessão autenticada/OTP e autorização por cliente. O modelo não recebe o cadastro
inteiro. O resultado do pedido omite e-mail, nome, telefone e ID do comprador.
O trace registra só ferramenta, sucesso e duração. A API recebe os textos e dados
necessários à resposta com `store=false`, sem garantia de ausência de retenção
operacional do provedor. Não reutilize sessões entre clientes diferentes.

## Configuração

| Variável | Padrão | Uso |
| --- | --- | --- |
| `OPENAI_API_KEY` | vazio | Obrigatória para atendimento |
| `OPENAI_MODEL` | `gpt-5-mini` | Modelo com Responses API e function calling |
| `EMPORIO_DATA_DIR` | `data` | Pasta dos seis CSVs |
| `EMPORIO_STATE_DIR` | `.state` | Histórico optativo da CLI |
| `EMPORIO_MAX_ROUNDS` | `6` | Entre 1 e 12 rodadas |

Variáveis de ambiente têm precedência sobre `.env`. Caminhos relativos são
resolvidos pela raiz. É possível usar `emporio --data-dir /caminho/data check`.
Os CSVs devem acompanhar a instalação; não estão embutidos no wheel.

O código distingue `credit_balance_exhausted`, limites de gastos/uso e limites
temporários de requisições. Falta de saldo exige regularizar o
[faturamento da API](https://platform.openai.com/settings/organization/billing/overview).
Veja os [códigos de erro oficiais](https://developers.openai.com/api/docs/guides/error-codes).
A aplicação não altera saldo ou limites na conta OpenAI.

## Organização

| Arquivo | Responsabilidade |
| --- | --- |
| `interface_chat_streamlit.py` | Tela do chat |
| `src/emporio/servico_de_conversa_da_interface.py` | Conectar interface, dados e agente |
| `src/emporio/agente_de_atendimento.py` | Loop de ferramentas e resposta |
| `src/emporio/repositorio_catalogo_e_pedidos.py` | Validação, SQL, preços e consultas aos CSVs |
| `src/emporio/ferramentas_de_consulta.py` | Schemas e execução das ferramentas |
| `src/emporio/integracao_modelo_openai.py` | Integração da Responses API e erros |
| `src/emporio/historico_de_conversas.py` | Histórico de conversa |
| `src/emporio/instrucoes_do_agente.py` | Persona, limites dos dados e comportamento |
| `src/emporio/configuracoes_da_aplicacao.py` | Ambiente e caminhos |
| `src/emporio/interface_linha_de_comando.py` | Interface de terminal |
| `src/emporio/utilitarios_texto_e_moeda.py` | Texto e valores monetários |
| `scripts/avaliar_atendimento_com_modelo_real.py` | Conversas com OpenAI real |

## Validação e conversas de exemplo

```bash
uv run emporio check
uv run ruff check .
uv run ruff format --check .
```

Os testes são mantidos **somente no computador**, em `tests/`, ignorados pelo Git
inclusive no histórico publicável e excluídos da distribuição. Execute localmente
`uv run pytest -q`. A CI pública valida os CSVs, código e formatação sem depender
de testes que não foram publicados. O transporte HTTP é isolado apenas nos testes
locais; a aplicação instalada usa a OpenAI real.

Para gerar cinco conversas reais em `examples/`:

```bash
# Exige chave e créditos; pode gerar cobrança.
uv run python scripts/avaliar_atendimento_com_modelo_real.py --output-dir examples
```

Os cenários cobrem catálogo, preço, promoção, pedido e informação indisponível.
O script não fabrica respostas quando a API falha. As conversas de entrega precisam
ser geradas com acesso válido ao modelo e revisadas antes de publicar.
Sem `--output-dir`, são gravadas em `.state/live/`.

## Limitações, uso de IA e entrega

Não há criação de compras, reservas, cancelamentos, reembolsos ou encaminhamentos.
Também não há cálculo de frete, regras de pagamento ou políticas de atendimento
fora dos campos dos CSVs. E-mail não substitui autenticação forte e o histórico
local não tem criptografia de aplicação ou expiração por tempo.

Com mais tempo: autenticação, integração com sistemas reais, streaming, métricas
de custo/latência, avaliação de respostas com LLM e política de retenção.

Usei OpenAI Codex para ler o desafio, implementar, testar e documentar o projeto.
A versão atual foi ajustada para consultar exclusivamente CSVs, conforme solicitação.
Não houve publicação no GitHub, envio de e-mail ou alteração de faturamento.
Para publicar após revisão, configure um repositório vazio e execute:

```bash
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

Não publique `.env`, `.state` ou credenciais. Respeite a data/hora de entrega
informada no processo seletivo; o e-mail e o prazo não estão nas fontes locais.
