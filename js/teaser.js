document.addEventListener('DOMContentLoaded', () => {
    const teaserContainer = document.getElementById('teaserContainer');
    if (!teaserContainer) return;
    fetch('data/sample_results.json').then(r => {
        if (!r.ok) throw new Error('No sample_results.json');
        return r.json();
    }).then(data => {
        const items = data.slice(0, 3);
        items.forEach((it, i) => {
            const card = document.createElement('div'); card.className = 'teaser-card';
            const persona = (it.group_prompt_template || '').replace(/\{[^}]+\}/g, '').slice(0, 80);
            const opts = Object.keys(it.human_answer||{}).slice(0,3).map(k=>`${k}:${Math.round((it.human_answer[k]||0)*100)}%`).join(' ');
            card.innerHTML = `
                <div class="teaser-meta"><strong>${it.dataset_name||'Dataset'}</strong> — ${it.Model||'Model'}</div>
                <div class="teaser-question">${(it.input_template||'').slice(0,140)}</div>
                <div class="teaser-stats">${opts}</div>
            `;
            teaserContainer.appendChild(card);
        });
    }).catch(err => {
        // silently fail if sample not present
        console.warn('Could not load teaser sample:', err);
    });
});
