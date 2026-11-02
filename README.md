# Empório da Música · Mel, assistente virtual

Agente de atendimento em **Python** para o desafio AI Engineer da Artefact.
A Mel consulta os CSVs da operação com ferramentas tipadas e busca as políticas
diretamente no PDF. Mantém o contexto da conversa, orienta sobre produtos e
pedidos e identifica situações que precisam de atendimento humano.

## Executar

Requisitos: Python 3.11+ e internet para instalar dependências.
Os arquivos originais já estão em `data/`. Execute os comandos **na raiz deste projeto**.

### Com uv

```bash
uv sync --frozen --extra dev
uv run emporio check
uv run emporio chat --provider demo
```

`check` valida os seis CSVs, as referências entre tabelas e a versão do manual, sem
chamar uma API. O modo `demo` funciona sem chave e sem rede após a instalação.
Ele é um **simulador determinístico com vocabulário limitado, não um LLM**.
Usa as mesmas ferramentas e o mesmo loop do agente para uma avaliação
reproduzível da camada de dados e das regras.

### Com pip

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
emporio check
emporio chat --provider demo
```

No PowerShell, ative com `.venv\Scripts\Activate.ps1`.
Com pip, substitua `uv run emporio` por `emporio` nos exemplos abaixo.

### Agente com LLM (OpenAI)

```bash
cp .env.example .env
# Edite .env e preencha OPENAI_API_KEY.
uv run emporio chat
```

Modelo padrão: `gpt-5-mini`, configurável em `OPENAI_MODEL`. O modo OpenAI exige
chave válida e saldo/cota no provedor; as chamadas podem gerar cobrança.
O programa não muda automaticamente para a demo se a API falhar: mostra o erro.

Exemplos de mensagens:

```text
Quais opções de violões disponíveis custam até R$ 1000?
Quanto custa o Takamine GD20 no PIX?
Qual o endereço e o horário da loja?
Qual o status do pedido 8?
Quanto fica o Ohana CK-20 em 6x? E no PIX?
Me arrependi da minha compra online. Recebi há três dias; posso devolver?
```

Mensagem única, ferramentas usadas e sessão persistente:

```bash
uv run emporio chat --provider demo --trace --message 'Quanto custa o Ohana CK-20 no PIX?'
uv run emporio chat --session avaliacao
uv run emporio chat --session avaliacao --message 'E quais as condições de pagamento?'
```

`/sair` encerra e `/limpar` apaga o histórico lógico da sessão atual. Sem `--session`,
o histórico existe somente em memória. Identificadores aceitam letras, números, `_`
e `-` (até 64 caracteres). Não reutilize a mesma sessão entre clientes diferentes.

Configuração em `.env` (variáveis do ambiente têm precedência):

| Variável | Padrão | Uso |
| --- | --- | --- |
| `OPENAI_API_KEY` | vazio | Chave, somente no modo OpenAI |
| `OPENAI_MODEL` | `gpt-5-mini` | Modelo com Responses API e function calling |
| `EMPORIO_DATA_DIR` | `data` | Pasta das fontes, relativa à raiz ou absoluta |
| `EMPORIO_STATE_DIR` | `.state` | Pasta do histórico optativo |
| `EMPORIO_MAX_ROUNDS` | `6` | Limite de rodadas do agente, entre 1 e 12 |

Também é possível usar `emporio --data-dir /caminho/para/data check`.
O `data/` deve acompanhar a distribuição do projeto; não é embutido no wheel.

## Arquitetura e decisões

```text
Cliente -> CLI -> agente (loop limitado) -> OpenAI Responses API
                   |                         |
                   |      chamadas de ferramentas tipadas
                   v                         v
                Toolbox / validação Pydantic
                   |          |             |
              SQLite      retrieval      regras Python
             em memória   BM25 do PDF     de cálculo
                   |          |
                 CSVs      manual PDF
```

**Abordagem híbrida: function calling + RAG lexical.** Preço, estoque, promoção e
pedido são informações estruturadas. Consultas parametrizadas são previsíveis
para esses dados. As políticas são recuperadas por seção com título e página.
Perguntas mistas podem usar mais de uma ferramenta no mesmo turno.

**Sem framework de agentes.** O loop em `agent.py` é explícito e testável, com
controle sobre argumentos, resultados, falhas e limites, sem a complexidade de
um grafo para um único agente.

**Modelo e provedor.** Escolhi OpenAI com `gpt-5-mini` como ponto de partida para
interpretar mensagens, escolher ferramentas e redigir respostas. O modelo pode ser
trocado por configuração; qualidade, latência e custo precisam ser medidos com a
conta do avaliador. A integração segue a
[Responses API e o fluxo oficial de function calling](https://developers.openai.com/api/docs/guides/function-calling).
Veja a [documentação do modelo](https://developers.openai.com/api/docs/models/gpt-5-mini).
Não há alegação de benchmark do modelo neste projeto.

**Retrieval.** O PDF é extraído com pdfplumber, sem OCR, e dividido pelos títulos
numerados. A sequência de seções diferencia títulos dos passos numerados dentro
da seção 7.2. BM25 com normalização de acentos e alguns sinônimos recupera trechos
relevantes. Para oito páginas, dispensa embeddings, serviço externo e custo de
indexação. BM25 não entende todas as paráfrases; o LLM pode reformular a busca.
Para um acervo maior, avaliaria retrieval híbrido e reranking.

**Dados e atualização.** Os CSVs são carregados em SQLite em memória. IDs, chaves
estrangeiras, datas, números, estoques e `specs` JSON são validados. Valores em BRL
viram centavos inteiros; descontos usam Decimal e arredondamento comercial. Os
nomes originais dos arquivos são preservados. Cada consulta verifica alterações
de tamanho/mtime nos CSVs e recarrega o conjunto validado; erros não servem valores
antigos silenciosamente. O PDF é verificado por SHA-256 e reindexado se mudar.
Isso consulta o **snapshot local atualizado**, sem integração de estoque em tempo real.

**Políticas calculáveis.** PIX, promoções, parcelas e janelas de devolução são
calculados em Python. O hash em `rules_snapshot.json` vincula esses cálculos ao manual
revisado: se o PDF mudar, param até revisão das regras e atualização deliberada do
hash. Não basta regenerar o hash sem conferir as políticas.

**Prompt.** Persona informal e profissional, uso obrigatório de fontes, consultas
distintas para dados/políticas, perguntas de esclarecimento, proteção de dados,
limites de escopo e proibição de fingir ações externas. O primeiro passo exige uma
ferramenta. Há até seis rodadas por padrão e doze chamadas no total por mensagem,
com limite de quatro chamadas em uma resposta. O SDK tem timeout de 30 segundos
por tentativa e até duas retentativas. A resposta pode demorar mais que 30 segundos
considerando rodadas e retentativas.

**Histórico e privacidade.** Apenas texto de cliente/resposta é mantido, limitado
às últimas vinte interações por sessão. Persistência local em SQLite é optativa,
com arquivo em `.state`, excluído do Git. A ferramenta de pedidos exige número e
e-mail coincidentes e só aceita e-mail que apareceu em mensagem do cliente.
O modelo não recebe o cadastro completo; o resultado do pedido omite nome, telefone,
e-mail e ID do cliente. `--trace` mostra ferramenta, sucesso e duração, sem
argumentos nem resultados. A API usa `store=false` e o histórico é reenviado pelo
cliente, sem depender de estado persistente do provedor. Isso não é garantia de
ausência de retenção operacional do provedor. Os textos e resultados necessários
às respostas são enviados à OpenAI no modo LLM.

## Ferramentas

| Ferramenta | Finalidade |
| --- | --- |
| `search_products` | Termos, categoria, teto de preço, disponibilidade e promoções ativas |
| `get_quote` | PIX, preço promocional ou parcelas com soma exata dos centavos |
| `get_order` | Consultar um pedido após verificar ID e e-mail |
| `search_policies` | Recuperar trechos com seção e página do PDF |
| `assess_return` | Orientar prazos com datas reais, sem aprovar uma devolução |

Não há SQL livre, shell, cadastro de clientes ou escrita de pedidos exposta ao
modelo. Dados recuperados são dados, não instruções. Isso reduz a superfície de
ataque; prompt injection e alucinação exigem avaliação adversarial com modelo real.

## Suposições e ambiguidades das fontes

- Só `status=active` **e** estoque positivo indicam disponibilidade. Um produto
  descontinuado com estoque positivo não é oferecido. `coming_soon` não é venda ativa.
- Só `is_active=1` oferece promoção; nome de campanha não comprova vigência.
  Havendo mais de uma ativa, usa-se a maior, sem acumular. PIX mantém o preço
  promocional sem desconto adicional. Não há reserva de estoque.
- A seção 3.1 prevalece sobre a tabela genérica da seção 3: 4–6x com parcela mínima
  de R$80, 7–12x com mínima de R$100. Para 2–3x abaixo de R$50 por parcela, a redação
  é ambígua e o cálculo pede confirmação humana.
- A seção 5.1 não cobre **exatamente R$500**. O prompt orienta confirmação humana;
  não há cálculo de frete externo.
- O telefone da capa/1.2 diverge do WhatsApp da seção 7. O e-mail aparece com e sem
  acento. O agente deve expor a divergência relevante, sem escolher silenciosamente.
  Horários especiais e feriados não são inferidos da data do sistema.
- Não há canal da compra nem data real de recebimento em `orders.csv`. Não uso
  `estimated_delivery` para arrependimento: peço esses dados ao cliente. Prazos usam
  a data atual em `America/Campo_Grande`, não a data dos pedidos do snapshot.
- No arrependimento, a data limite é recebimento + 7 dias, inclusive. Em defeito,
  a janela da seção 4.2 parte da compra e não apaga a garantia de 90 dias da seção
  8.1. Troca por preferência tem marco inicial pouco claro e pede análise humana.
  Não são decisões jurídicas nem negativas automáticas de direitos.
- Há 65 produtos nos CSVs, apesar da descrição institucional citar mais de 300.
  A oferta efetiva usa somente as linhas disponíveis, sem inventar o restante.
- Totais históricos de pedidos não são recalculados com preços atuais: podem
  refletir condições da época, frete ou descontos não representados nas tabelas.

## Exemplos e validação

As cinco conversas em `examples/` foram geradas com a demo e as ferramentas reais,
com data de referência fixa, identificadas como **sem LLM**:

1. `01_catalogo_e_preco.md`: orçamento e preço do Takamine com PIX.
2. `02_endereco_e_horario.md`: informações gerais recuperadas do manual.
3. `03_promocao_e_parcelamento.md`: promoção sem PIX adicional e parcela abaixo do mínimo.
4. `04_pedido_e_privacidade.md`: identificação em dois turnos e recusa de listar clientes.
5. `05_devolucao_com_contexto.md`: esclarecimento de canal/data e aplicação dos sete dias.

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/generate_examples.py
```

Os testes cobrem importação e atualização de fontes, consultas parametrizadas,
estoque/status, promoções, parcelas, datas, retrieval com evidências, identificação
do pedido, sessões, erros e limites. O adaptador OpenAI é testado com **SDK real
e transporte HTTP simulado**, verificando o JSON e a sequência de
`function_call` / `function_call_output`.

**Não houve chamada a LLM real na implementação:** não havia chave configurada.
Os testes não provam qualidade linguística nem aderência do modelo ao prompt.
Para avaliar o provedor real com sua chave, gere cinco novas conversas:

```bash
# Faz chamadas reais, possivelmente cobradas. Transcrições ficam em .state/live/.
uv run python scripts/evaluate_live.py
```

Esse script verifica ferramentas e alguns resultados esperados; é uma avaliação
de fumaça, não um benchmark nem uma avaliação jurídica.

## Limitações e próximos passos

- **E-mail não é autenticação forte.** Serve ao protótipo com dados fictícios;
  produção exigiria sessão autenticada/OTP e autorização por cliente antes de
  publicar como atendimento público.
- Histórico local sem criptografia de aplicação, expiração por tempo ou limpeza
  forense. `/limpar` remove linhas; não promete apagar disco/backups.
- Sem compras, reservas, cancelamentos, reembolsos, envio de mensagens ou abertura
  de chamados. Reclamações orientam contato humano, sem alegar encaminhamento automático.
- Sem WhatsApp, transportadora, CEP, CRM ou calendário de feriados/dias úteis.
  Não inventa frete ou prazo exato de retorno humano.
- Armazenamento e recarga não foram projetados para múltiplos processos concorrentes.
  A interface é CLI.
- Regras/alertas referem-se ao manual 2.1 fornecido. Atualização exige revisar código,
  prompt, alertas, testes e hash. Não há OCR.
- Com mais tempo: autenticação, sistemas reais, avaliação adversarial com LLM,
  métricas de groundedness/latência/custo, streaming, avaliação de retrieval,
  retenção de dados e revisão do manual com a gerência.

## Uso de assistente de código e entrega

Usei **OpenAI Codex** para ler as fontes, estruturar e implementar a solução,
escrever testes, executar a validação e gerar exemplos/documentação. As skills
`pdf` e `openai-docs` auxiliaram a leitura dos PDFs e a consulta à documentação
oficial. Os exemplos não foram apresentados como conversas com modelo real.

O Git local registra etapas reais em commits separados. Não houve force-push,
publicação remota ou envio de e-mail. Para concluir o entregável de repositório
público, crie um repositório vazio na sua conta e publique após revisar o conteúdo:

```bash
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

Revise se os materiais fornecidos podem constar em repositório público e nunca
publique `.env`, `.state` ou credenciais. Respeite a data e o horário de entrega;
o e-mail e seu prazo não estão presentes nas fontes locais.

