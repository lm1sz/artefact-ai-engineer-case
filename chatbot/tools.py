"""Allowlisted tools with server-side authorization and deterministic business rules."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from .data import Store, normalizar_texto


@dataclass(frozen=True)
class Session:
    # A aplicação fornece a identidade; mensagens e argumentos não podem alterá-la.
    customer_id: int | None = None


def formatar_dinheiro(value: Decimal) -> str:
    """Arredonda um Decimal para duas casas e retorna texto.
    Round a Decimal to two places and return text.
    """
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


POLICY_TOPICS = {
    "store": [1, 2], "hours": [2], "payments": [3, 6],
    "returns": [4, 7, 8], "shipping": [4, 5], "promotions": [6, 7],
    "warranty": [4, 7, 8], "privacy": [7, 8], "service": [6, 7, 8],
}


class Tools:
    def __init__(self, store: Store, session: Session | None = None, today: date | None = None):
        """Associa dados, identidade da sessao e data local da loja.
        Bind data, session identity and the store local date.
        """
        self.store = store
        self.session = session or Session()
        self.today = today or datetime.now(ZoneInfo("America/Campo_Grande")).date()
        self.denied = 0

    def executar(self, name: str, arguments: object) -> dict:
        """Valida nome, campos, tipos e limites antes de executar a ferramenta permitida.
        """
        # 1. Procura a ferramenta na lista permitida.
        esquema = PARAMETROS_FERRAMENTAS.get(name) if isinstance(name, str) else None
        if esquema is None:
            return {"error": "tool_not_allowed"}
        # 2. Exige um dicionário com exatamente os campos declarados.
        if not isinstance(arguments, dict) or set(arguments) != set(esquema["properties"]):
            return {"error": "invalid_arguments"}
        # 3. Confere cada tipo, valor nulo permitido e opção enumerada.
        for key, value in arguments.items():
            rule = esquema["properties"][key]
            types = rule["type"] if isinstance(rule["type"], list) else [rule["type"]]
            if value is None and "null" in types:
                continue
            valid = (("string" in types and isinstance(value, str) and len(value) <= 500)
                     or ("integer" in types and type(value) is int)
                     or ("number" in types and type(value) in (int, float))
                     or ("boolean" in types and type(value) is bool))
            if not valid or ("enum" in rule and value not in rule["enum"]):
                return {"error": "invalid_arguments"}
            # 4. Rejeita valores não finitos e números fora dos limites.
            if isinstance(value, (float, int)) and not isinstance(value, bool):
                if (value < rule.get("minimum", 0) or value > rule.get("maximum", 10**9)
                        or not math.isfinite(value)):
                    return {"error": "invalid_arguments", "field": key,
                            "minimum": rule.get("minimum", 0), "maximum": rule.get("maximum", 10**9),
                            "action": "Correct this argument using the declared bounds and retry the tool."}
        try:
            # 5. Executa só após validar; a ferramenta verifica as regras de negócio e acesso.
            result = getattr(self, name)(**arguments)
            # Mascara os dados reconhecidos como proteção adicional; autorização ocorre antes.
            return json.loads(self.store.mascarar_dados(json.dumps(result, ensure_ascii=False)))
        # 6. Converte estas falhas previstas em um erro estruturado.
        except (ValueError, KeyError, TypeError, ArithmeticError):
            return {"error": "invalid_arguments_or_data", "action": "Ask for clarification or human review."}

    def _montar_produto(self, row: dict) -> dict:
        """Combina produto, estoque e maior promocao ativa, sem acumular PIX.
        Combine product, stock and highest active promotion without stacking PIX.
        """
        price = Decimal(row["price_brl"])
        discounts = [Decimal(p["discount_percent"]) for p in self.store.tables["promotions"]
                     if p["product_id"] == row["product_id"] and p["is_active"] == "1"]
        discount = max(discounts, default=Decimal(0))
        available = row["status"] == "active" and int(row["stock_quantity"]) > 0
        offer = price * (1 - discount / 100) if available else price
        return {
            "product_id": int(row["product_id"]), "name": row["name"],
            "category": self.store.categories[row["category_id"]],
            # Descriptions remain searchable locally, but marketing prose is not
            # needed in the model payload or the structured product presentation.
            "specs": json.loads(row["specs"]),
            "status": row["status"], "stock_quantity": int(row["stock_quantity"]),
            "available": available, "list_price_brl": formatar_dinheiro(price),
            "promotion_percent": str(discount if available else 0),
            "selling_price_brl": formatar_dinheiro(offer),
            "pix_price_brl": formatar_dinheiro(offer if discount and available else price * Decimal("0.95")),
            "discounts_stack": False, "source": "products.csv + promotions.csv",
            "promotion_basis": "is_active flag; source has no validity dates",
        }

    def _ofertas_ativas(self) -> list[dict]:
        """Seleciona ofertas de produtos disponiveis em todo o catalogo.
        Select available product offers across the entire catalog.
        """
        # Calcula detalhes somente para produtos com promoção positiva ativa.
        promoted_ids = {int(p["product_id"]) for p in self.store.tables["promotions"]
                        if p["is_active"] == "1" and Decimal(p["discount_percent"]) > 0}
        offers = [self._montar_produto(row) for product_id, row in self.store.products.items()
                  if product_id in promoted_ids]
        return [p for p in offers if p["available"] and Decimal(p["promotion_percent"]) > 0]

    def listar_promocoes(self, category_id: int | None, max_price_brl: float | None,
                              limit: int) -> dict:
        # Filtra o catálogo inteiro antes do limite para não omitir ofertas de outras páginas.
        """Filtra todas as ofertas antes de limitar a lista; informa os totais.
        Filter all offers before limiting the list; report total counts.
        """
        offers = self._ofertas_ativas()
        matches = [p for p in offers
                   if (category_id is None or int(self.store.products[p["product_id"]]["category_id"]) == category_id)
                   and (max_price_brl is None or Decimal(p["selling_price_brl"]) <= Decimal(str(max_price_brl)))]
        matches.sort(key=lambda p: (-Decimal(p["promotion_percent"]),
                                    Decimal(p["selling_price_brl"]), p["product_id"]))
        return {"products": matches[:limit], "total_matches": len(matches),
                "catalog_active_promotion_count": len(offers), "has_more": len(matches) > limit,
                "coverage": "Entire catalog checked; filters applied before result limit",
                "source_kind": "supplied static snapshot",
                "promotion_basis": "is_active=1 and product available; no validity dates provided",
                "discounts_stack": False}

    def buscar_produtos(self, query: str, max_price_brl: float | None,
                        available_only: bool, limit: int, category_id: int | None = None) -> dict:
        # Exige todos os termos no texto combinado; não executa SQL nem código do modelo.
        """Busca termos e aplica categoria, estoque e orcamento antes do limite.
        Match terms and apply category, stock and budget filters before the limit.
        """
        words = normalizar_texto(query).split()
        products = []
        for row in self.store.products.values():
            if category_id is not None and int(row["category_id"]) != category_id:
                continue
            haystack = normalizar_texto(" ".join([row["name"], row["description"], row["specs"],
                                           self.store.categories[row["category_id"]]]))
            if not all(word in haystack for word in words):
                continue
            item = self._montar_produto(row)
            if available_only and not item["available"]:
                continue
            if max_price_brl is not None and Decimal(item["selling_price_brl"]) > Decimal(str(max_price_brl)):
                continue
            products.append(item)
        products.sort(key=lambda p: (not p["available"], Decimal(p["selling_price_brl"]), p["product_id"]))
        return {"products": products[:limit], "total_matches": len(products),
                "has_more": len(products) > limit,
                "catalog_active_promotion_count": len(self._ofertas_ativas()),
                "coverage": "Matches for these filters only; not the whole catalog. Use listar_promocoes to list offers.",
                "budget_basis": "selling_price_brl before optional PIX discount",
                "as_of": str(self.today), "source_kind": "supplied static snapshot"}

    def detalhar_produto(self, product_id: int) -> dict:
        """Retorna especificacoes e precos calculados de um produto existente.
        """
        row = self.store.products.get(product_id)
        return self._montar_produto(row) if row else {"error": "product_not_found"}

    def consultar_politica(self, topic: str) -> dict:
        """Recupera paginas completas por assunto e informa ambiguidades da fonte.
        Retrieve complete pages by topic and report source ambiguities.
        """
        return {
            "topic": topic, "source": "políticas_da_loja.pdf", "version": "2.1 / June 2025",
            "excerpts": [{"page": p, "text": self.store.paginas_politica[p - 1]}
                         for p in POLICY_TOPICS[topic]],
            "ambiguities": [
                "Phone/WhatsApp and email differ between sections: do not pick an unverified contact.",
                "Installment table and detailed section differ: use section 3.1 for estimates, confirm with staff.",
                "Shipping fee at exactly BRL 500 is undefined: confirm with staff.",
                "Do not apply final-sale or customization exclusions to deny statutory rights automatically; escalate.",
            ],
        }

    def _pedido_autorizado(self, order_id: int) -> dict | None:
        """Retorna o pedido somente se pertencer ao cliente da sessao.
        """
        order = self.store.orders.get(order_id)
        if (self.session.customer_id is None or order is None
                or int(order["customer_id"]) != self.session.customer_id):
            self.denied += 1
            return None
        return order

    def _negar_acesso(self) -> dict:
        """Nega sem revelar existencia do pedido; repeticoes apenas sugerem revisao.
        Deny without revealing order existence; repeated denials only suggest review.
        """
        return {"error": "order_access_denied", "message": "Authenticate through the application or contact staff.",
                "human_review_recommended": self.denied >= 3,
                "note": "Repeated denied access is a risk signal, not evidence of fraud."}

    def consultar_pedido(self, order_id: int) -> dict:
        """Verifica acesso e retorna somente campos permitidos do pedido.
        """
        order = self._pedido_autorizado(order_id)
        if order is None:
            return self._negar_acesso()
        # Retorna só campos permitidos; exclui identidade, contatos e notas livres.
        result = {key: order[key] for key in ("order_id", "order_date", "status", "total_brl",
                                               "payment_method", "tracking_code", "estimated_delivery")}
        result["items"] = [{"quantity": int(r["quantity"]),
                            "name": self.store.products[int(r["product_id"])]["name"]}
                           for r in self.store.tables["order_items"] if int(r["order_id"]) == order_id]
        if order["status"] == "cancelled":
            reasons = {"Pedido cancelado pelo cliente antes do processamento": "customer_cancelled",
                       "Item fora de estoque no momento do pedido": "out_of_stock",
                       "Pagamento não confirmado dentro do prazo": "payment_not_confirmed",
                       "Endereço de entrega inválido informado pelo cliente": "invalid_delivery_address"}
            result["cancellation_reason"] = reasons.get(order["notes"], "requires_staff_review")
        result["tracking_note"] = "Stored code only; no carrier integration or live shipment updates."
        result["source_kind"] = "supplied static snapshot"
        result["actual_received_date"] = None
        result["purchase_channel"] = None
        result["receipt_date_warning"] = "Actual receipt date and purchase channel are absent from this source. Neither order_date, estimated_delivery nor delivered status establishes when the customer received the product."
        if order["estimated_delivery"]:
            result["estimate_in_past"] = date.fromisoformat(order["estimated_delivery"]) < self.today
        return result

    def avaliar_devolucao(self, order_id: int, reason: str, received_date: str | None,
                      online_purchase: bool | None, original_condition: bool | None) -> dict:
        """Verifica acesso, datas e fatos ausentes; apenas avalia, sem emitir reembolso.
        """
        order = self._pedido_autorizado(order_id)
        if order is None:
            return self._negar_acesso()
        base = {"assessment_only": True, "refund_issued": False,
                "source": "políticas_da_loja.pdf sections 4 and 8",
                "facts_basis": "Order snapshot plus unverified customer-provided answers",
                "human_review_required": True}
        if order["status"] == "cancelled":
            return {**base, "outcome": "staff_review", "explanation": "Order is cancelled; verify any payment/refund with staff."}
        if order["status"] != "delivered":
            return {**base, "outcome": "staff_review", "explanation": "Snapshot does not confirm delivery; clarify delivery or cancellation request."}
        receipt = date.fromisoformat(received_date) if received_date else None
        purchase = date.fromisoformat(order["order_date"])
        if receipt and (receipt > self.today or receipt < purchase):
            return {**base, "outcome": "inconsistent_dates", "explanation": "Receipt date must be between purchase date and today. Clarify; do not infer fraud."}
        if reason == "defect":
            days = (self.today - purchase).days
            return {**base, "outcome": "staff_review", "days_since_purchase": days,
                    "explanation": "Store exchange route within 30 days of purchase; manufacturer/assisted warranty route afterwards. The manual also describes a 90-day legal warranty from receipt. Staff must assess the defect and applicable rights; do not deny solely on this calculation.",
                    "missing": ["actual receipt confirmation", "defect assessment", "manufacturer warranty certificate"]}
        missing = []
        if receipt is None:
            missing.append("actual receipt date")
        if original_condition is None:
            missing.append("original packaging/condition")
        if reason == "regret" and online_purchase is None:
            missing.append("online purchase confirmation")
        if missing:
            return {**base, "outcome": "needs_information", "missing": missing,
                    "eligibility_determined": False,
                    "deadline_determined": receipt is not None,
                    "response_guidance": "Ask only for the missing facts. Do not say the receipt was long ago or the return deadline expired based on order date, estimate or delivered status. If the customer cannot establish receipt, ask staff to verify it."}
        days = (self.today - receipt).days
        within = days <= 7 and original_condition and (reason != "regret" or online_purchase)
        return {**base, "outcome": "potentially_eligible" if within else "staff_review",
                "days_since_receipt": days,
                "explanation": "Manual describes a 7-calendar-day window. Customer answers and item exceptions need staff confirmation. No return has been opened."}

    def cotar_pagamento(self, product_id: int, quantity: int, method: str, installments: int) -> dict:
        """Valida estoque e parcelas e calcula uma cotacao com Decimal, sem cobrar.
        """
        product = self.detalhar_produto(product_id)
        if "error" in product:
            return product
        if not product["available"] or quantity > product["stock_quantity"]:
            return {"error": "insufficient_stock"}
        unit = Decimal(product["pix_price_brl"] if method == "pix" else product["selling_price_brl"])
        total = unit * quantity
        if method != "credit" and installments != 1:
            return {"error": "installments_require_credit"}
        minimum = Decimal(50 if installments <= 3 else 80 if installments <= 6 else 100)
        if method == "credit" and total / installments < minimum:
            # Sugere um limite calculado; o cliente ainda escolhe e pede nova cotacao.
            allowed = [count for count in range(1, 13)
                       if total / count >= (50 if count <= 3 else 80 if count <= 6 else 100)]
            return {"error": "installment_below_minimum", "minimum_brl": formatar_dinheiro(minimum),
                    "product_id": product_id, "product_name": product['name'],
                    "requested_installments": installments,
                    "total_brl": formatar_dinheiro(total),
                    "max_allowed_installments": max(allowed, default=0),
                    "shipping_included": False, "quote_only": True,
                    "note": "No payment made. Ask the customer to choose a supported count, then quote again. Section 3.1; staff confirmation required."}
        # Divide em centavos e distribui a sobra: a soma fecha e a diferença é de até R$ 0,01.
        base_cents, extra_cents = divmod(int(total * 100), installments)
        amounts = [formatar_dinheiro(Decimal(base_cents + (i < extra_cents)) / 100)
                   for i in range(installments)]
        return {"product_id": product_id, "product_name": product["name"], "quantity": quantity,
                "unit_price_brl": formatar_dinheiro(unit),
                "total_brl": formatar_dinheiro(total), "method": method, "installments": installments,
                "installment_minimum_brl": formatar_dinheiro(minimum) if method == 'credit' else None,
                "installment_rule": "Section 3.1: 1-3 installments minimum BRL 50; 4-6 minimum BRL 80; 7-12 minimum BRL 100. A price-specific maximum is not a store-wide cap.",
                "interest_percent": 0,
                "installment_amounts_brl": amounts,
                "promotion_percent": product["promotion_percent"], "discounts_stack": False,
                "shipping_included": False, "quote_only": True,
                "note": "Exact installment amounts sum to total_brl. Rules follow detailed section 3.1; conflicting summary requires staff confirmation."}


def campo(kind, **kwargs):
    """Descreve um parametro no JSON Schema da ferramenta.
    Describe one parameter in the tool JSON Schema.
    """
    return {"type": kind, **kwargs}


def definir_schema(name, description, properties):
    """Declara ferramenta e parametros obrigatorios; rejeita campos extras.
    Declare a tool and required parameters; disallow extra fields.
    """
    return {"type": "function", "name": name, "description": description, "strict": True,
            "parameters": {"type": "object", "properties": properties,
                           "required": list(properties), "additionalProperties": False}}


SCHEMAS = [
    definir_schema("buscar_produtos", "Search factual catalog. Use short terms; broaden on zero matches. Filter category to avoid matching another instrument mentioned in a description. category_id: 1 guitars, 2 bass, 3 drums/percussion, 4 keyboards/pianos, 5 acoustic/classical guitars (violões), 6 woodwinds, 7 brass, 8 orchestral strings, 9 ukuleles. Compare returned specs; never invent them.", {
        "query": campo("string"), "max_price_brl": campo(["number", "null"], minimum=0),
        "available_only": campo("boolean"), "limit": campo("integer", minimum=1, maximum=8),
        "category_id": campo(["integer", "null"], minimum=1, maximum=9)}),
    definir_schema("listar_promocoes", "List active available offers across the ENTIRE catalog, even outside cheap search pages. Required for promotion questions. Null filters mean all categories/budgets; zero filtered matches does not mean no offers elsewhere. Returns original price, discount, final price and total counts.", {
        "category_id": campo(["integer", "null"], minimum=1, maximum=9),
        "max_price_brl": campo(["number", "null"], minimum=0),
        "limit": campo("integer", minimum=1, maximum=8)}),
    definir_schema("detalhar_produto", "Get exact specifications, stock and calculated current snapshot prices.", {
        "product_id": campo("integer", minimum=1)}),
    definir_schema("consultar_politica", "Retrieve complete relevant pages of source policies, including exceptions and ambiguity notes.", {
        "topic": campo("string", enum=list(POLICY_TOPICS))}),
    definir_schema("consultar_pedido", "Read one order after server-side session ownership check. Cannot authenticate by chat or tool arguments.", {
        "order_id": campo("integer", minimum=1)}),
    definir_schema("avaliar_devolucao", "Assess a return/warranty route, never execute. Ask for missing customer facts; never invent receipt date or use estimated delivery as actual receipt.", {
        "order_id": campo("integer", minimum=1), "reason": campo("string", enum=["regret", "preference", "defect"]),
        "received_date": campo(["string", "null"], description="Actual receipt date explicitly stated by the CUSTOMER, YYYY-MM-DD. Otherwise null. NEVER copy an order date or estimated delivery from a tool."),
        "online_purchase": campo(["boolean", "null"], description="True or false ONLY if the CUSTOMER explicitly stated the purchase channel. Otherwise null; a regret request does not establish an online purchase."),
        "original_condition": campo(["boolean", "null"], description="True ONLY when the CUSTOMER confirms unused/original condition, original packaging and all included items. False when a required condition is explicitly unmet. Otherwise null. Having the box alone is NOT enough to confirm this field.")}),
    definir_schema("cotar_pagamento", "Calculate prices without stacking PIX and promotions; validate stock and credit installments. No purchase is executed.", {
        "product_id": campo("integer", minimum=1), "quantity": campo("integer", minimum=1, maximum=100),
        "method": campo("string", enum=["pix", "credit", "debit", "boleto"]),
        "installments": campo("integer", minimum=1, maximum=12)}),
]

# As mesmas regras alimentam a API e a validação local, sem busca repetida na lista.
PARAMETROS_FERRAMENTAS = {tool["name"]: tool["parameters"] for tool in SCHEMAS}
