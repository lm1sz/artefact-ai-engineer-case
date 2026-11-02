# 01 budget and payment

OFFLINE REFERENCE — scripted tool calls and fixed reference replies; no model/API execution

Session: guest

**Customer:** I am a beginner. Which nylon-string guitars are available for up to BRL 1000?

**Assistant:** Showing 3 of 5 matching instruments in the catalog snapshot: Tagima Memphis AC-39 Nylon Natural (id 83), BRL 429.90, 15 in stock; Rozini RC-104 Nylon Estudante (id 85), BRL 459.90, 10 in stock; Yamaha C40 Nylon Natural (id 81), BRL 599.90, 12 in stock. These match your nylon-string preference and budget. For a beginner, compare the documented neck/scale and electronics against how you plan to play; I would not assume solid wood from the wood name alone. Is this mainly for practice or amplified performance?

Tools: buscar_produtos

**Customer:** What is the PIX price for the Yamaha C40, product 81?

**Assistant:** The pix quote for 1 Yamaha C40 Nylon Natural is BRL 569.91, excluding shipping. Payments: 1 x BRL 569.91. The 5% PIX discount applies because this item has no active promotion. Payment rules: policy section 3.1, subject to staff confirmation. This is a quote from the supplied snapshot, not a placed order.

Tools: cotar_pagamento

**Customer:** And for one of those, can I pay in 12 credit-card installments instead?

**Assistant:** Twelve installments do not meet the BRL 100.00 minimum per payment. For this BRL 599.90 quote, up to 6 installments are supported by detailed policy section 3.1, subject to staff confirmation. Shipping is excluded. Would you like a quote for six installments?

Tools: cotar_pagamento

**Customer:** Six, then.

**Assistant:** The credit quote for 1 Yamaha C40 Nylon Natural is BRL 599.90, excluding shipping. Payments: 2 x BRL 99.99; 4 x BRL 99.98. Credit installments use the regular or promotional price, without the PIX discount. Payment rules: policy section 3.1, subject to staff confirmation. This is a quote from the supplied snapshot, not a placed order.

Tools: cotar_pagamento

## Review criteria

Check product continuity, PIX versus credit totals, refusal of 12 installments, and the exact sum for six payments. Quotes must exclude shipping.

Automated call checks: no flags
Answer quality still requires human review; these checks are not a model-quality score.
