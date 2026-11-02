# 04 return missing receipt

OFFLINE REFERENCE — scripted tool calls and fixed reference replies; no model/API execution

Session: local demo customer 3

**Customer:** I regret my purchase of order 1. Am I eligible for a return?

**Assistant:** I need a little more information to assess the return. When did you actually receive it? If unknown, staff must verify it; an estimate cannot replace it. Please confirm any still-unknown condition details: unused, original packaging and all included items. The box alone is insufficient. Was this an online purchase? The manual describes a seven-calendar-day regret window after receipt for online purchases (section 4.1, page 4). The estimated delivery date is not proof of receipt. Staff must confirm eligibility; no return or refund has been opened.

Tools: consultar_politica, avaliar_devolucao

**Customer:** I bought it online and still have the box.

**Assistant:** I need a little more information to assess the return. When did you actually receive it? If unknown, staff must verify it; an estimate cannot replace it. You confirmed the box. Is the product unused, with all included items? The manual describes a seven-calendar-day regret window after receipt for online purchases (section 4.1, page 4). The estimated delivery date is not proof of receipt. Staff must confirm eligibility; no return or refund has been opened.

Tools: avaliar_devolucao

**Customer:** It is unused, in the original packaging, with every included item.

**Assistant:** I need a little more information to assess the return. When did you actually receive it? If unknown, staff must verify it; an estimate cannot replace it. The manual describes a seven-calendar-day regret window after receipt for online purchases (section 4.1, page 4). The estimated delivery date is not proof of receipt. Staff must confirm eligibility; no return or refund has been opened.

Tools: avaliar_devolucao

**Customer:** I do not remember when it arrived. Can you use the estimated delivery date?

**Assistant:** We cannot use the delivery estimate as proof of when you received the order. Please ask staff to verify the actual receipt date. You have already confirmed the online purchase and complete original condition; the receipt date remains missing, so I cannot determine the seven-day return window (policy section 4.1, page 4). No return or refund has been opened.

Tools: avaliar_devolucao

## Review criteria

Keep receipt unknown across all turns. The box alone does not establish full condition. Ask only for remaining facts; never announce expiry or issue a refund.

Automated call checks: no flags
Answer quality still requires human review; these checks are not a model-quality score.
