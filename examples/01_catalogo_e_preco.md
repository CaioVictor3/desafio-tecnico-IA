# 01 catalogo e preco

Execução real do modo DEMO determinístico, sem LLM/API. Ferramentas consultam os CSVs/PDF fornecidos. Data de referência fixa: 2026-11-02 (America/Campo_Grande).

**Cliente:** Quais opções de violões disponíveis até R$ 1000?

**Mel:** Consultei o catálogo local:
- Tagima Memphis AC-39 Nylon Natural: R$ 429,90; 15 em estoque.
- Rozini RC-104 Nylon Estudante: R$ 459,90; 10 em estoque.
- Shelby SN-100 Folk Aço Preto: R$ 549,00; 5 em estoque.
- Giannini GF-1R Aço Folk Sunburst: R$ 579,90; 7 em estoque.
- Yamaha C40 Nylon Natural: R$ 599,90; 12 em estoque.
Há mais opções com esses filtros. Posso refinar a busca.
Fonte: products.csv + categories.csv + promotions.csv.

Ferramentas: search_products.

**Cliente:** Quanto custa o Takamine GD20 no PIX?

**Mel:** Takamine GD20 Dreadnought Natural: R$ 2.089,05 no pix. Frete não incluído. Fontes: products.csv, promotions.csv e manual 3/6.2.

Ferramentas: search_products, get_quote.
