# 02 store information

OFFLINE REFERENCE — scripted tool calls and fixed reference replies; no model/API execution

Session: guest

**Customer:** Where is the store and what are the regular opening hours?

**Assistant:** The manual lists Rua 14 de Maio, 3200, Centro, Campo Grande/MS, CEP 79202-333. Regular hours are Monday–Friday 09:00–18:00 and Saturday 09:00–13:00, local Campo Grande time; closed Sundays and holidays (policy page 2). Special schedules need staff confirmation.

Tools: consultar_politica, consultar_politica

**Customer:** Show me up to three instruments on promotion, across all categories.

**Assistant:** The snapshot has 4 offers matching your filters; showing 3: Ohana CK-20 Concert Natural: BRL 549.00 -> BRL 439.20 (20% off); Crafter HT-100 Folk Aço Natural: BRL 2399.00 -> BRL 1967.18 (18% off); Kalani KAL-700T Tenor Natural: BRL 359.00 -> BRL 323.10 (10% off). PIX does not stack with these discounts. Active flags are snapshot data; staff must confirm current validity.

Tools: listar_promocoes

**Customer:** Only ukuleles under BRL 1000, please. Can PIX stack with those offers?

**Assistant:** The snapshot has 2 offers matching your filters; showing 2: Ohana CK-20 Concert Natural: BRL 549.00 -> BRL 439.20 (20% off); Kalani KAL-700T Tenor Natural: BRL 359.00 -> BRL 323.10 (10% off). PIX does not stack with these discounts. Active flags are snapshot data; staff must confirm current validity.

Tools: listar_promocoes, consultar_politica

## Review criteria

Check address/hours against page 2; do not claim today's opening. Three displayed promotions are not the whole catalog. Preserve the ukulele/budget filter and never stack PIX.

Automated call checks: no flags
Answer quality still requires human review; these checks are not a model-quality score.
