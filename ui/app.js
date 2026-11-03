const form = document.querySelector('#chat-form');
const input = document.querySelector('#message');
const messages = document.querySelector('#messages');
const intro = document.querySelector('#intro');
const conversation = document.querySelector('#conversation');
const send = document.querySelector('#send');
const reset = document.querySelector('#reset');
const status = document.querySelector('.status');
let csrf = '';
let busy = false;
let cooldownUntil = 0;

// A browser retry cannot increase the provider's quota. Keep repeated sends
// disabled until the server's indicated waiting period has elapsed.
setInterval(() => {
  const remaining = Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000));
  send.disabled = busy || !csrf || remaining > 0;
  send.title = remaining ? `Aguarde ${remaining}s antes de tentar novamente` : 'Enviar mensagem';
}, 1000);

// Text nodes keep user and model content out of HTML execution.
function inline(parent, text) {
  for (const [i, part] of text.split(/\*\*(.*?)\*\*/g).entries()) {
    if (i % 2) { const strong = document.createElement('strong'); strong.textContent = part; parent.append(strong); }
    else parent.append(document.createTextNode(part));
  }
}
function render(parent, text) {
  parent.replaceChildren();
  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) continue;
    if (line.trim().startsWith('|') && /^\s*\|?[\s:|\-]+\|?\s*$/.test(lines[i + 1] || '')) {
      const table = document.createElement('table'); table.className = 'answer-table';
      const row = (s, tag) => { const tr = document.createElement('tr');
        for (const cell of s.trim().replace(/^\||\|$/g, '').split('|')) {
          const td = document.createElement(tag); inline(td, cell.trim()); tr.append(td);
        } table.append(tr);
      };
      row(line, 'th'); i++;
      while ((lines[i + 1] || '').trim().startsWith('|')) row(lines[++i], 'td');
      const wrap = document.createElement('div'); wrap.className = 'table-wrap'; wrap.append(table); parent.append(wrap);
    } else {
      const p = document.createElement('p'); inline(p, line.replace(/^#{1,4}\s+/, '').replace(/^[-*]\s+/, '• ')); parent.append(p);
    }
  }
}
function addAssistant(text) {
  const outer = document.createElement('div'); outer.className = 'message assistant';
  const label = document.createElement('div'); label.className = 'assistant-label'; label.textContent = 'EMPÓRIO · ASSISTENTE';
  const content = document.createElement('div'); content.className = 'assistant-content'; render(content, text);
  outer.append(label, content); messages.append(outer); return content;
}
function controls(value) { busy = value; send.disabled = value || !csrf || Date.now() < cooldownUntil; reset.disabled = value || !csrf; }
function scrollToEnd() { conversation.scrollTop = conversation.scrollHeight; }
async function post(path, body) {
  const response = await fetch(path, { method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }, body: JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 429 && Number.isFinite(data.retry_after) && data.retry_after > 0) {
      cooldownUntil = Date.now() + data.retry_after * 1000;
    }
    throw new Error(data.error || 'Não foi possível concluir a solicitação.');
  }
  return data;
}
async function submit(text) {
  text = text.trim(); if (!text || busy || !csrf || Date.now() < cooldownUntil) return;
  controls(true); intro.hidden = true;
  const outer = document.createElement('div'); outer.className = 'message user';
  const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = text;
  outer.append(bubble); messages.append(outer); input.value = ''; input.style.height = 'auto';
  const answer = addAssistant('Consultando…'); scrollToEnd();
  try {
    const result = await post('/api/chat', { message: text }); render(answer, result.answer);
    const details = document.createElement('details'); details.className = 'source';
    const summary = document.createElement('summary'); summary.textContent = 'Consultas realizadas';
    const list = document.createElement('p'); list.textContent = result.tools.join(', ');
    details.append(summary, list); answer.append(details);
  } catch (error) { render(answer, 'Não consegui concluir: ' + error.message); }
  finally { controls(false); scrollToEnd(); input.focus(); }
}
form.addEventListener('submit', event => { event.preventDefault(); submit(input.value); });
input.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); submit(input.value); }
});
input.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 110) + 'px'; });
document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => submit(button.dataset.prompt)));
reset.addEventListener('click', async () => {
  if (busy || !csrf) return; controls(true);
  try { await post('/api/reset', {}); messages.replaceChildren(); intro.hidden = false; }
  catch (error) { addAssistant(error.message); }
  finally { controls(false); input.focus(); }
});
controls(true);
fetch('/api/session', { credentials: 'same-origin' }).then(async response => {
  const data = await response.json(); if (!response.ok) throw new Error(data.error);
  csrf = data.csrf;
  status.textContent = `${data.model} · ${data.demo_customer_id ? 'cliente demonstrativo ' + data.demo_customer_id : 'sessão visitante'}`;
  controls(false);
}).catch(() => { status.textContent = 'Servidor indisponível'; addAssistant('Abra esta interface pelo servidor local do chatbot.'); controls(false); });
