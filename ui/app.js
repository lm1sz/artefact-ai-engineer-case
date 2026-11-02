const form = document.querySelector('#chat-form');
const input = document.querySelector('#message');
const messages = document.querySelector('#messages');
const intro = document.querySelector('#intro');
const conversation = document.querySelector('#conversation');
const followups = document.querySelector('#followups');
const send = document.querySelector('#send');
let pending = null;
let busy = false;

const guitar = (color) => `<svg class="guitar" viewBox="0 0 100 130" aria-hidden="true"><path d="M46 5h8l2 43c15-5 25 8 18 20-3 5-1 9 4 15 17 24-2 42-28 42S5 107 22 83c5-6 7-10 4-15-7-12 3-25 18-20z" fill="${color}" stroke="#8f6c42" stroke-width="1.5"/><path d="M46 5h8v63h-8z" fill="#584334"/><circle cx="50" cy="80" r="10" fill="#453c2c"/><circle cx="50" cy="80" r="13" fill="none" stroke="#b38a50"/><path d="M39 103h22v5H39z" fill="#584334"/><path d="M48 6v98m4-98v98" stroke="#e9d7ae" stroke-width=".8"/><path d="M46 12h8m-8 8h8m-8 8h8m-8 8h8" stroke="#aaa18d"/></svg>`;
const source = (text) => `<details class="source"><summary>↳ Ver referência desta demonstração</summary><p>${text}</p></details>`;
const product = (name,price,stock,color) => `<article class="product">${guitar(color)}<small>VIOLÃO · NYLON</small><strong>${name}</strong><div class="price">${price}</div><div class="stock">${stock} no estoque de exemplo</div></article>`;

function response(text) {
  const q = text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  if (/pix|parcel|pagamento/.test(q)) return {
    html: '<h3>Um passo mais perto do seu som.</h3><p>No exemplo do <strong>Yamaha C40 Nylon Natural</strong>, o valor é <strong>R$ 599,90</strong>. No PIX, a cotação de referência fica em <strong>R$ 569,91</strong>, sem frete.</p><p>É uma simulação com o catálogo fornecido. Nenhum pagamento ou pedido é realizado aqui.</p>' + source('Cotação pré-calculada de chatbot/examples/reference/01_budget_and_payment.md. Esta tela não executa cotar_pagamento nem consulta dados ao vivo.'),
    suggestions: ['Ver violões até R$ 1.000', 'Como funciona a devolução?']
  };
  if (/devol|troca|arrepend|garantia/.test(q)) return {
    html: '<h3>Vamos entender sua compra.</h3><p>Para avaliar uma devolução por arrependimento, preciso saber: <strong>a compra foi online, quando você recebeu o produto e ele está sem uso, com a embalagem original e todos os itens?</strong></p><p>O exemplo de referência considera a política de sete dias corridos após o recebimento para compras online. A elegibilidade precisa de confirmação da equipe.</p><p>Nesta prévia, não consultamos pedidos nem abrimos devoluções.</p>' + source('Fluxo ilustrativo baseado em chatbot/examples/reference/04_return_missing_receipt.md e na seção 4.1 da política. Não constitui uma avaliação de um pedido real.'),
    suggestions: ['Encontrar um violão para começar', 'Como pagar com PIX?']
  };
  if (/pedido|rastre|entrega|admin|cliente/.test(q)) return {
    html: '<h3>Seu pedido merece atenção. Seus dados também.</h3><p>Uma consulta de pedido precisa estar vinculada a uma sessão autenticada. Informar apenas o número do pedido não autoriza o acesso.</p><p>Esta é uma demonstração visual, sem autenticação ou conexão com pedidos. Na versão integrada, essa conversa usaria a identidade verificada da sessão para consultar somente os pedidos autorizados.</p>' + source('Comportamento ilustrativo da checagem de titularidade do backend Python. Nenhum acesso a pedidos foi executado.'),
    suggestions: ['Ver instrumentos até R$ 1.000', 'Como funciona a devolução?']
  };
  if (/viol|guit|instrument|1000|1.000|comec|iniciante|yamaha|nylon/.test(q)) return {
    html: '<h3>Seu primeiro violão, com espaço para crescer.</h3><p>Para começar com cordas de nylon, estas são três opções do catálogo de exemplo dentro de <strong>R$ 1.000</strong>:</p><div class="products">' + product('Tagima Memphis AC-39','R$ 429,90',15,'#d9b57b') + product('Rozini RC-104 Estudante','R$ 459,90',10,'#b98b56') + product('Yamaha C40 Natural','R$ 599,90',12,'#e1c38d') + '</div><p>Você pretende tocar principalmente em casa ou precisa ligar o instrumento em uma caixa? Isso ajuda a orientar a escolha.</p>' + source('Valores e estoque do exemplo offline em chatbot/examples/reference/01_budget_and_payment.md. Ilustrações genéricas dos instrumentos. Esta tela não consulta estoque em tempo real.'),
    suggestions: ['Quanto fica o Yamaha no PIX?', 'Como funciona a devolução?']
  };
  return {
    html: '<h3>Vamos encontrar o seu ritmo.</h3><p>Esta prévia tem respostas de exemplo para <strong>violões até R$ 1.000, pagamento por PIX, acompanhamento de pedidos e devoluções</strong>.</p><p>Experimente um dos assuntos abaixo. Quando conectarmos o agente Python, ele poderá interpretar sua mensagem e consultar as ferramentas da loja.</p>',
    suggestions: ['Quero um violão até R$ 1.000', 'Acompanhar meu pedido', 'Como funciona a devolução?']
  };
}

function scrollToEnd() { conversation.scrollTop = conversation.scrollHeight; }
function addAssistant(html) {
  const element = document.createElement('div');
  element.className = 'message assistant';
  element.innerHTML = '<div class="assistant-label"><span class="avatar">e</span> EMPÓRIO · RESPOSTA DE EXEMPLO</div><div class="assistant-content">' + html + '</div>';
  messages.append(element);
  return element;
}
function setFollowups(items) {
  followups.replaceChildren();
  for (const text of items) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = text;
    button.addEventListener('click', () => submit(text));
    followups.append(button);
  }
}
function submit(text) {
  text = text.trim();
  if (!text || busy) return;
  busy = true;
  send.disabled = true;
  intro.hidden = true;
  followups.replaceChildren();
  const element = document.createElement('div');
  element.className = 'message user';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  element.append(bubble);
  messages.append(element);
  input.value = '';
  input.style.height = 'auto';
  const loading = addAssistant('<span class="typing" aria-label="Preparando exemplo">•••</span>');
  scrollToEnd();
  pending = setTimeout(() => {
    const result = response(text);
    loading.querySelector('.assistant-content').innerHTML = result.html;
    setFollowups(result.suggestions);
    busy = false;
    send.disabled = false;
    pending = null;
    scrollToEnd();
    input.focus();
  }, 650);
}
form.addEventListener('submit', (event) => { event.preventDefault(); submit(input.value); });
input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); submit(input.value); }
});
input.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight,110) + 'px'; });
document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => submit(button.dataset.prompt)));
document.querySelector('#reset').addEventListener('click', () => {
  clearTimeout(pending);
  pending = null;
  busy = false;
  send.disabled = false;
  messages.replaceChildren();
  followups.replaceChildren();
  intro.hidden = false;
  input.value = '';
  input.style.height = 'auto';
  conversation.scrollTop = 0;
  input.focus();
});
