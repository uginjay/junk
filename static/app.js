const form = document.getElementById('factForm');
const statusEl = document.getElementById('status');
const resultsEl = document.getElementById('results');
const runBtn = document.getElementById('runBtn');

function setStatus(msg, type = 'info') {
  statusEl.textContent = msg;
  statusEl.className = `status ${type}`;
}

function renderResults(data) {
  const { summary, claims } = data;
  const s = summary || {};
  const header = `\nИтог: всего ${s.total_claims ?? 0}, Подтверждено: ${s.Supported ?? 0}, Опровергнуто: ${s.Refuted ?? 0}, Неопределенно: ${s.Uncertain ?? 0}`;

  const items = (claims || []).map(c => {
    const fc = c.fact_check || {};
    const ev = c.evidence || [];
    const cites = (fc.citations || []).map(ct => `<li><a href="${ct.url}" target="_blank" rel="noopener">${ct.title || ct.url}</a></li>`).join('');
    const evList = ev.map(e => `<li><a href="${e.url}" target="_blank" rel="noopener">${e.title || e.url}</a><div class="snippet">${e.snippet || ''}</div></li>`).join('');
    return `
      <div class="claim">
        <div class="claim-text">${c.text}</div>
        <div class="verdict ${String(fc.verdict).toLowerCase()}">
          Вердикт: <b>${fc.verdict || 'Uncertain'}</b> (уверенность: ${(fc.confidence ?? 0).toFixed(2)})
        </div>
        <div class="rationale">${fc.rationale || ''}</div>
        <div class="section">
          <div class="section-title">Цитаты</div>
          <ul>${cites}</ul>
        </div>
        <div class="section">
          <div class="section-title">Найденные источники</div>
          <ul>${evList}</ul>
        </div>
      </div>
    `;
  }).join('');

  resultsEl.innerHTML = `
    <div class="summary">${header}</div>
    ${items}
  `;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  resultsEl.innerHTML = '';

  const openai_api_key = document.getElementById('openaiKey').value.trim();
  const yandex_user = document.getElementById('yandexUser').value.trim();
  const yandex_key = document.getElementById('yandexKey').value.trim();
  const max_claims = parseInt(document.getElementById('maxClaims').value, 10) || 6;
  const max_results = parseInt(document.getElementById('maxResults').value, 10) || 5;
  const draft = document.getElementById('draft').value.trim();

  // Save for convenience (local only)
  localStorage.setItem('openaiKey', openai_api_key);
  localStorage.setItem('yandexUser', yandex_user);
  localStorage.setItem('yandexKey', yandex_key);

  if (!draft || !openai_api_key || !yandex_user || !yandex_key) {
    setStatus('Пожалуйста, заполните все поля', 'error');
    return;
  }

  runBtn.disabled = true;
  setStatus('Работаем... Это может занять 10-40 секунд.');

  try {
    const resp = await fetch('/api/factcheck', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft, openai_api_key, yandex_user, yandex_key, max_claims, max_results })
    });
    const data = await resp.json();
    if (!resp.ok) {
      console.error('Error', data);
      setStatus(`Ошибка: ${data.error || 'Неизвестная ошибка'}`, 'error');
      return;
    }
    setStatus('Готово', 'success');
    renderResults(data);
  } catch (err) {
    console.error(err);
    setStatus('Сетевая ошибка. Проверьте консоль.', 'error');
  } finally {
    runBtn.disabled = false;
  }
});

