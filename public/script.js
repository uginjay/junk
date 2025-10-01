const el = (id) => document.getElementById(id);

function verdictBadge(verdict) {
  const v = (verdict || 'unclear').toLowerCase();
  const cls = v === 'supported' ? 'supported' : v === 'refuted' ? 'refuted' : 'unclear';
  const label = v === 'supported' ? 'Подтверждено' : v === 'refuted' ? 'Опровергнуто' : 'Неясно';
  return `<span class="badge ${cls}">${label}</span>`;
}

function renderResults(data) {
  const container = el('results');
  container.innerHTML = '';
  if (!data || !Array.isArray(data.report) || data.report.length === 0) {
    container.innerHTML = '<div class="small">Нет результатов.</div>';
    return;
  }

  data.report.forEach((item, idx) => {
    const j = item.judgment || {};
    const evidence = item.evidence || [];

    const cites = evidence.map((e, i) => {
      const href = e.link || e.url || '#';
      const title = e.title || href;
      const snippet = e.snippet || '';
      return `<li><a class="cite" href="${href}" target="_blank" rel="noopener">${title}</a><div class="small">${snippet}</div></li>`;
    }).join('');

    const html = `
      <div class="card">
        <div>${verdictBadge(j.verdict)} <strong>Тезис ${idx + 1}:</strong> ${item.statement || ''}</div>
        <div class="small" style="margin:6px 0 10px;">Уверенность: ${(j.confidence ?? 0).toFixed(2)}</div>
        <div style="margin: 6px 0 10px;">${(j.rationale || '')}</div>
        <div><strong>Источники</strong></div>
        <ul>${cites}</ul>
      </div>
    `;
    const node = document.createElement('div');
    node.innerHTML = html;
    container.appendChild(node);
  });
}

async function run() {
  const text = el('inputText').value.trim();
  const language = el('language').value;
  const maxClaims = Number(el('maxClaims').value || 5);
  const maxPerClaim = Number(el('maxPerClaim').value || 3);

  if (!text) {
    el('status').textContent = 'Введите текст';
    return;
  }

  el('runBtn').disabled = true;
  el('status').textContent = 'Анализ текста и поиск источников...';
  el('results').innerHTML = '';

  try {
    const resp = await fetch('/api/factcheck', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, language, max_claims: maxClaims, max_results_per_claim: maxPerClaim })
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    el('status').textContent = 'Готово';
    renderResults(data);
  } catch (e) {
    el('status').textContent = `Ошибка: ${e.message}`;
  } finally {
    el('runBtn').disabled = false;
  }
}

window.addEventListener('DOMContentLoaded', () => {
  el('runBtn').addEventListener('click', run);
});