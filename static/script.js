async function checkFacts() {
    const textInput = document.getElementById('textInput');
    const text = textInput.value.trim();
    
    // Clear previous results
    document.getElementById('results').style.display = 'none';
    document.getElementById('error').style.display = 'none';
    
    // Validation
    if (!text) {
        showError('Пожалуйста, введите текст для проверки');
        return;
    }
    
    // Show loading
    document.getElementById('loading').style.display = 'block';
    document.getElementById('checkButton').disabled = true;
    
    try {
        const response = await fetch('/api/check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка при проверке фактов');
        }
        
        displayResults(data);
        
    } catch (error) {
        showError(error.message);
    } finally {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('checkButton').disabled = false;
    }
}

function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    const resultsContent = document.getElementById('resultsContent');
    
    let html = `
        <div class="stats">
            Проверено фактов: ${data.facts_checked}
        </div>
    `;
    
    data.results.forEach((result, index) => {
        const verdictClass = result.verdict.toLowerCase().replace(/\s+/g, '_');
        
        html += `
            <div class="fact-card verdict-${verdictClass}">
                <div class="fact-text">${index + 1}. ${escapeHtml(result.fact)}</div>
                <span class="verdict ${verdictClass}">${result.verdict}</span>
                <div class="explanation">${escapeHtml(result.explanation)}</div>
                ${result.sources && result.sources.length > 0 ? `
                    <div class="sources">
                        <h4>Источники:</h4>
                        ${result.sources.map(source => `
                            <a href="${escapeHtml(source.link)}" target="_blank" class="source-link">
                                <span class="source-title">${escapeHtml(source.title)}</span>
                                <span class="source-snippet">${escapeHtml(source.snippet)}</span>
                            </a>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    });
    
    resultsContent.innerHTML = html;
    resultsDiv.style.display = 'block';
    
    // Scroll to results
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    errorDiv.scrollIntoView({ behavior: 'smooth' });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Allow Enter key to submit (with Ctrl/Cmd)
document.getElementById('textInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        checkFacts();
    }
});
