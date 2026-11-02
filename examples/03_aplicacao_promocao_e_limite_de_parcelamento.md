# 03 aplicacao promocao e limite de parcelamento

Execução real do modo DEMO determinístico, sem LLM/API. Ferramentas consultam os CSVs/PDF fornecidos. Data de referência fixa: 2026-11-02 (America/Campo_Grande).

**Cliente:** Quanto custa o Ohana CK-20 no PIX?

**Mel:** Ohana CK-20 Concert Natural: R$ 439,20 no PIX. De R$ 549,00 por R$ 439,20 (20% de desconto). PIX não acumula desconto sobre a promoção. Frete não incluído. Fontes: products.csv, promotions.csv e manual 3/6.2.

Ferramentas: search_products, get_quote.

**Cliente:** E em 6x?

**Mel:** O valor por parcela fica abaixo do mínimo desta faixa. Fonte: manual, seção 3.1.

Ferramentas: search_products, get_quote.
