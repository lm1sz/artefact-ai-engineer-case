# 03 order tracking

OFFLINE REFERENCE — scripted tool calls and fixed reference replies; no model/API execution

Session: local demo customer 3

**Customer:** What is the status of my order 1? Can you track its delivery live?

**Assistant:** Your order snapshot shows status 'delivered', order date 2025-10-15, payment method pix, and stored tracking code BRAB1234567BR. The stored delivery estimate is 2025-10-25; this old estimate is not a live update. I cannot query a carrier from this prototype. Staff should confirm current delivery information.

Tools: consultar_pedido

## Review criteria

Check ownership and source fields; never claim live carrier access or treat the estimate as receipt.

Automated call checks: no flags
Answer quality still requires human review; these checks are not a model-quality score.
