"""Presentation checks for Portuguese/English and Python-calculated quotes."""
from collections import Counter
import re

from .data import normalizar_texto


# Deliberately small language hint, not a general translator. Short follow-ups
# inherit the conversation language when neither vocabulary gives evidence.
ENGLISH = set('hi hello show me three my am the what which where when how can could would please under bought received it is are you your with for instead six then only remember arrived pay price those'.split())
PORTUGUESE = set('oi ola obrigado obrigada sim nao qual quais onde quando como posso pode voce seu sua com para quero tenho ate sou seis entao apenas recebi comprei chegou pagar preco pedido vezes cartao frete moro'.split())


def detectar_idioma(text: str, default: str | None = None) -> str | None:
    words = re.findall(r'[a-z]+', normalizar_texto(text))
    english = sum(w in ENGLISH for w in words)
    portuguese = sum(w in PORTUGUESE for w in words)
    if english > portuguese:
        return 'en'
    if portuguese > english:
        return 'pt'
    return default


def moeda(value: str, language: str) -> str:
    return ('R$ ' + value.replace('.', ',')) if language == 'pt' else 'BRL ' + value


# Only structured catalog fields enter product recommendations. Marketing prose
# is omitted: translating/rephrasing it could strengthen a claim unintentionally.
SPEC_LABELS = {
    'top': ('Tampo', 'Top'), 'back_sides': ('Fundo/laterais', 'Back/sides'),
    'neck': ('Braço', 'Neck'), 'strings': ('Cordas', 'Strings'),
    'scale': ('Escala', 'Scale'), 'electronics': ('Eletrônica', 'Electronics'),
    'color': ('Cor', 'Color'), 'body': ('Corpo', 'Body'),
    'shells': ('Cascos', 'Shells'), 'pieces': ('Peças', 'Pieces'),
    'hardware': ('Ferragens', 'Hardware'), 'keys': ('Teclas', 'Keys'),
    'type': ('Tipo', 'Type'), 'polyphony': ('Polifonia', 'Polyphony'),
}


def resposta_catalogo(calls: list[dict], language: str) -> str | None:
    """Present retrieved facts without letting the LLM embellish specifications."""
    attempts = [c for c in calls if c['name'] in (
        'buscar_produtos', 'listar_promocoes', 'detalhar_produto')]
    if not attempts:
        return None
    catalog = [c for c in attempts if not c['result'].get('error')]
    if not catalog:
        return ('Não consegui recuperar os dados do produto no catálogo. Não posso confirmar suas características. '
                'Pode confirmar o modelo ou consultar a equipe?' if language == 'pt' else
                'I could not retrieve the product data from the catalog, so I cannot confirm its characteristics. '
                'Could you confirm the model or check with staff?')
    # The last search supersedes earlier filters. Subsequent detail calls enrich
    # only its products, rather than reintroducing an item outside those filters.
    last_search = next((i for i in range(len(catalog)-1, -1, -1)
                        if catalog[i]['name'] != 'detalhar_produto'), None)
    selected = catalog[last_search:] if last_search is not None else catalog
    search = selected[0]['result'] if last_search is not None else None
    products = {p['product_id']: p for p in search['products']} if search is not None else {}
    for entry in selected:
        if entry['name'] == 'detalhar_produto':
            product = entry['result']
            if search is None or product['product_id'] in products:
                products[product['product_id']] = product
    pt = language == 'pt'
    if not products:
        return ('A consulta ao catálogo não retornou produtos para esses filtros. Quer ajustar o orçamento ou a busca?'
                if pt else 'The catalog query returned no products for these filters. Would you like to adjust the budget or search?')
    header = ('Estas são as opções retornadas pelo catálogo; compare os preços e as especificações documentadas:'
              if pt else 'These are the options returned by the catalog; compare their prices and documented specifications:')
    if search is not None:
        header += (f' Exibindo {len(products)} de {search["total_matches"]} resultados.' if pt else
                   f' Showing {len(products)} of {search["total_matches"]} results.')
    blocks = [header]
    for product in products.values():
        price = moeda(product['selling_price_brl'], language)
        stock = (f'Estoque no catálogo: {product["stock_quantity"]}.' if pt else
                 f'Catalog stock: {product["stock_quantity"]}.')
        availability = ('Disponível' if pt else 'Available') if product['available'] else ('Indisponível' if pt else 'Unavailable')
        lines = [f'**{product["name"]} (ID {product["product_id"]}) — {price}.** {availability}. {stock}']
        # Values remain verbatim: "Spruce" must never become "solid Spruce".
        specs = product.get('specs', {})
        details = [f'{labels[0 if pt else 1]}: {specs[key]}' for key, labels in SPEC_LABELS.items() if key in specs]
        lines.append(('Especificações do catálogo: ' if pt else 'Catalog specifications: ') +
                     ('; '.join(details) if details else ('não informadas' if pt else 'not provided')) + '.')
        if product.get('pix_price_brl') is not None:
            lines.append(f'PIX: {moeda(product["pix_price_brl"], language)}. ' +
                         ('PIX não acumula com promoções.' if pt else 'PIX does not stack with promotions.'))
        if product.get('promotion_percent') not in (None, '0'):
            lines.append(('Desconto registrado: ' if pt else 'Recorded discount: ') + f'{product["promotion_percent"]}%.')
        blocks.append('\n'.join(lines))
    blocks.append(
        'Fonte: products.csv + promotions.csv (dados estáticos; confirme preço e disponibilidade com a equipe). '
        'As especificações acima não permitem concluir características adicionais de construção, timbre, conforto ou durabilidade. '
        'O que não está documentado precisa de confirmação da equipe. Qual opção você quer comparar?'
        if pt else
        'Source: products.csv + promotions.csv (static snapshot; confirm price and availability with staff). '
        'The specifications above do not establish additional construction, tone, comfort or durability characteristics. '
        'Anything undocumented needs staff confirmation. Which option would you like to compare?')
    return '\n\n'.join(blocks)


def resposta_pagamentos(calls: list[dict], language: str) -> str | None:
    """Render only supported payment results; never recompute amounts in prose."""
    quotes = [c['result'] for c in calls if c['name'] == 'cotar_pagamento'
              and c['result'].get('error') in (None, 'installment_below_minimum')]
    if not quotes:
        return None
    blocks = []
    for quote in quotes:
        name = quote.get('product_name', 'Produto' if language == 'pt' else 'Product')
        total = moeda(quote['total_brl'], language)
        if quote.get('error') == 'installment_below_minimum':
            requested = quote['requested_installments']
            minimum = moeda(quote['minimum_brl'], language)
            maximum = quote['max_allowed_installments']
            if language == 'pt':
                blocks.append(f'**{name}: {total}.** Não é possível parcelar em {requested} vezes: essa faixa exige parcela mínima de {minimum}. '
                              f'Para este valor, o máximo permitido é {maximum} vezes. Qual quantidade de parcelas você prefere?')
            else:
                blocks.append(f'**{name}: {total}.** A {requested}-installment plan is unavailable: that range requires at least {minimum} per payment. '
                              f'This price supports up to {maximum} installments. How many would you prefer?')
            continue
        method = quote['method']
        if method == 'credit':
            # These cent amounts already passed business-rule validation. Grouping
            # them preserves exact totals (e.g. 2 x 99.99 + 4 x 99.98 = 599.90).
            groups = Counter(quote['installment_amounts_brl'])
            schedule = ' + '.join(f"{count} × {moeda(amount, language)}" for amount, count in groups.items())
            minimum = moeda(quote['installment_minimum_brl'], language)
            if language == 'pt':
                blocks.append(f'**{name} — cartão de crédito:** {quote["installments"]} parcelas sem juros: **{schedule}**. '
                              f'**Total: {total}.** A parcela mínima desta faixa é {minimum}. O desconto de PIX não se aplica ao cartão.')
            else:
                blocks.append(f'**{name} — credit card:** {quote["installments"]} interest-free payments: **{schedule}**. '
                              f'**Total: {total}.** The minimum for this range is {minimum}. The PIX discount does not apply to credit cards.')
        else:
            label = {'pix': 'PIX', 'debit': 'débito' if language == 'pt' else 'debit', 'boleto': 'boleto'}[method]
            blocks.append(f'**{name} — {label}: {total}** ' + ('à vista.' if language == 'pt' else 'in one payment.'))
    footer = ('Frete não incluído. Cotação sujeita à confirmação da equipe conforme a seção 3.1 da política; nenhum pagamento foi realizado.'
              if language == 'pt' else
              'Shipping excluded. Staff must confirm the quote under policy section 3.1; no payment was made.')
    return '\n\n'.join([*blocks, footer])


def oferta_fora_do_escopo(text: str) -> bool:
    """Catch the observed recipe offer without treating a refusal as an offer."""
    normalized = normalizar_texto(text)
    patterns = (
        r'\b(?:i can|i could|happy to)\s+(?:still\s+)?(?:help|share|provide|teach|give)[^.!?\n]{0,100}\b(?:recipe|recipes|baking)\b',
        r'\b(?:if you.d like|would you like)[^.!?\n]{0,70}\b(?:recipe|baking)\b',
        r'\b(?:posso|podemos|vou)\s+(?:te\s+)?(?:ajudar|ensinar|passar|compartilhar)[^.!?\n]{0,90}\b(?:receita|receitas|culinaria)\b',
        r'\b(?:here is|here.s|ingredients|ingredientes|modo de preparo)[^.!?\n]{0,70}\b(?:recipe|receita|bread|pao)\b',
    )
    for pattern in patterns:
        for match in re.finditer(pattern, normalized):
            # "não posso ajudar com receitas" and "I can help with instruments,
            # not recipes" are refusals, not the positive offer we are blocking.
            if re.search(r'\bnao\s*$', normalized[max(0, match.start()-8):match.start()]):
                continue
            if re.search(r'\b(?:not|nao)\b', match.group()):
                continue
            return True
    return False


def redirecionar_escopo(language: str, private_request: bool) -> str:
    if language == 'en':
        denial = "I can't disclose customer records or bypass order access checks. " if private_request else ''
        return denial + 'I can help with musical instruments, payments, authorized orders and store policies. What would you like to know about Empório da Música?'
    denial = 'Não posso divulgar cadastros de clientes nem ignorar a autorização de pedidos. ' if private_request else ''
    return denial + 'Posso ajudar com instrumentos musicais, pagamentos, pedidos autorizados e políticas da loja. O que você gostaria de saber sobre o Empório da Música?'
