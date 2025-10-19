"use strict";

// Simple client-side results explorer
let allData = [];
let filteredData = [];
let currentPage = 1;
let itemsPerPage = 25;
let availableModels = [];

document.addEventListener('DOMContentLoaded', () => {
  initializeControls();
  initializeExampleLoading();
});

function initializeExampleLoading() {
  const loadSampleBtn = document.getElementById('loadSampleBtn');
  const loadSelectedBtn = document.getElementById('loadSelectedBtn');
  if (loadSampleBtn) loadSampleBtn.addEventListener('click', () => displayResults(generateSampleData()));
  if (loadSelectedBtn) loadSelectedBtn.addEventListener('click', async () => {
    const sel = document.getElementById('sampleFileSelect').value;
    try {
      const resp = await fetch(sel);
      if (!resp.ok) throw new Error('File not found: ' + sel);
      const data = await resp.json();
      displayResults(data);
    } catch (e) {
      console.warn('Could not load selected example file:', e);
      alert('Could not load selected example file. Make sure it exists in /website/data/ (or use sample data).');
    }
  });

  // Auto-load a small teaser sample
  const autoLoad = true;
  if (autoLoad) {
    const sample = generateSampleData();
    displayResults(sample.slice(0, 100));
  }
}

function generateSampleData() {
  const datasets = ['OpinionQA', 'WisdomOfCrowds', 'ChaosNLI', 'MoralMachine'];
  const models = ['gpt-4', 'claude-3', 'llama-3-70b'];
  const countries = ['United States', 'Kenya', 'Germany', 'Brazil'];
  const data = [];
  for (let i = 0; i < 200; i++) {
    const numOpts = [2, 3, 4, 5][Math.floor(Math.random() * 4)];
    const options = ['A', 'B', 'C', 'D', 'E'].slice(0, numOpts);
    let remaining = 1.0;
    const human = {};
    for (let j = 0; j < options.length; j++) {
      if (j === options.length - 1) human[options[j]] = remaining;
      else {
        const v = Math.random() * remaining * 0.6;
        human[options[j]] = v;
        remaining -= v;
      }
    }
    const hsum = Object.values(human).reduce((a, b) => a + b, 0);
    Object.keys(human).forEach(k => human[k] /= hsum);
    const model = {};
    const corr = 0.7 + Math.random() * 0.3;
    Object.keys(human).forEach(k => { model[k] = Math.max(0.001, human[k] * corr + (1 - corr) * (1 / options.length) * Math.random()); });
    const msum = Object.values(model).reduce((a, b) => a + b, 0);
    Object.keys(model).forEach(k => model[k] /= msum);

    data.push({
      dataset_name: datasets[Math.floor(Math.random() * datasets.length)],
      input_template: `Sample question ${i + 1}: What would you choose in this hypothetical scenario?`,
      group_prompt_template: 'You are an Amazon Mechanical Turk worker from {country}.',
      group_prompt_variable_map: { country: countries[Math.floor(Math.random() * countries.length)] },
      human_answer: human,
      Response_Distribution: model,
      Model: models[Math.floor(Math.random() * models.length)],
      Prompt_Method: 'token_prob',
      group_size: Math.floor(100 + Math.random() * 1000)
    });
  }
  return data;
}

function displayResults(data) {
  allData = data.map((item, idx) => ({ ...item, index: idx, kl_divergence: calculateKLDivergence(item.human_answer || {}, item.Response_Distribution || {}) }));
  filteredData = [...allData];
  availableModels = [...new Set(allData.map(d => d.Model).filter(Boolean))].sort();
  updateSummaryStats();
  populateFilters();
  const rs = document.getElementById('resultsSection'); 
  if (rs) rs.style.display = 'block';
  currentPage = 1;
  renderQuestions();
}

function updateSummaryStats() {
  const statDataset = document.getElementById('statDataset');
  const statModel = document.getElementById('statModel');
  const statQuestions = document.getElementById('statQuestions');
  const statAvgKL = document.getElementById('statAvgKL');
  const datasets = [...new Set(allData.map(d => d.dataset_name))];
  const models = [...new Set(allData.map(d => d.Model))];
  const avgKL = allData.length ? (allData.reduce((s, d) => s + d.kl_divergence, 0) / allData.length) : 0;
  if (statDataset) statDataset.textContent = datasets.length > 1 ? `${datasets.length} datasets` : (datasets[0] || '-');
  if (statModel) statModel.textContent = models.length > 1 ? `${models.length} models` : (models[0] || '-');
  if (statQuestions) statQuestions.textContent = allData.length;
  if (statAvgKL) statAvgKL.textContent = avgKL.toFixed(3);
}

function populateFilters() {
  const datasets = [...new Set(allData.map(d => d.dataset_name))].sort();
  const datasetFilter = document.getElementById('datasetFilter');
  const modelFilter = document.getElementById('modelFilter');
  if (!datasetFilter || !modelFilter) return;
  datasetFilter.innerHTML = '<option value="all">All Datasets</option>';
  datasets.forEach(ds => { 
    const o = document.createElement('option'); 
    o.value = ds; 
    o.textContent = ds; 
    datasetFilter.appendChild(o); 
  });
  modelFilter.innerHTML = '<option value="all">All Models</option>';
  availableModels.forEach(m => { 
    const o = document.createElement('option'); 
    o.value = m; 
    o.textContent = m; 
    modelFilter.appendChild(o); 
  });
}

function initializeControls() {
  const df = document.getElementById('datasetFilter'); 
  if (df) df.addEventListener('change', applyFilters);
  const mf = document.getElementById('modelFilter'); 
  if (mf) mf.addEventListener('change', applyFilters);
  const si = document.getElementById('searchInput'); 
  if (si) si.addEventListener('input', applyFilters);
  const ss = document.getElementById('sortSelect'); 
  if (ss) ss.addEventListener('change', applySorting);
  const ipp = document.getElementById('itemsPerPage'); 
  if (ipp) ipp.addEventListener('change', (e) => { 
    itemsPerPage = parseInt(e.target.value) || 25; 
    currentPage = 1; 
    renderQuestions(); 
  });
  const prev = document.getElementById('prevPage'); 
  if (prev) prev.addEventListener('click', () => { 
    if (currentPage > 1) { 
      currentPage--; 
      renderQuestions(); 
    } 
  });
  const next = document.getElementById('nextPage'); 
  if (next) next.addEventListener('click', () => { 
    const totalPages = Math.ceil(filteredData.length / itemsPerPage); 
    if (currentPage < totalPages) { 
      currentPage++; 
      renderQuestions(); 
    } 
  });
  const prevB = document.getElementById('prevPageBottom'); 
  if (prevB) prevB.addEventListener('click', () => { 
    if (currentPage > 1) { 
      currentPage--; 
      renderQuestions(); 
    } 
  });
  const nextB = document.getElementById('nextPageBottom'); 
  if (nextB) nextB.addEventListener('click', () => { 
    const totalPages = Math.ceil(filteredData.length / itemsPerPage); 
    if (currentPage < totalPages) { 
      currentPage++; 
      renderQuestions(); 
    } 
  });
}

function applyFilters() {
  const datasetVal = (document.getElementById('datasetFilter') || {}).value || 'all';
  const modelVal = (document.getElementById('modelFilter') || {}).value || 'all';
  const searchTerm = ((document.getElementById('searchInput') || {}).value || '').toLowerCase();
  filteredData = allData.filter(item => {
    const okDataset = datasetVal === 'all' || item.dataset_name === datasetVal;
    const okModel = modelVal === 'all' || (item.Model && item.Model === modelVal);
    const okSearch = !searchTerm || (item.input_template || '').toLowerCase().includes(searchTerm);
    return okDataset && okModel && okSearch;
  });
  currentPage = 1; 
  applySorting();
}

function applySorting() {
  const sortBy = (document.getElementById('sortSelect') || {}).value || 'index';
  switch (sortBy) {
    case 'kl-asc': 
      filteredData.sort((a, b) => a.kl_divergence - b.kl_divergence); 
      break;
    case 'kl-desc': 
      filteredData.sort((a, b) => b.kl_divergence - a.kl_divergence); 
      break;
    case 'index': 
    default: 
      filteredData.sort((a, b) => a.index - b.index); 
      break;
  }
  renderQuestions();
}

function renderQuestions() {
  const container = document.getElementById('questionsContainer'); 
  if (!container) return; 
  container.innerHTML = '';
  const totalPages = Math.max(1, Math.ceil(filteredData.length / itemsPerPage));
  const startIdx = (currentPage - 1) * itemsPerPage; 
  const endIdx = Math.min(startIdx + itemsPerPage, filteredData.length);
  const pageData = filteredData.slice(startIdx, endIdx);
  pageData.forEach(item => { 
    container.appendChild(createQuestionCard(item)); 
  });
  updatePaginationControls(totalPages);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updatePaginationControls(totalPages) {
  const cur = document.getElementById('currentPage'); 
  const tot = document.getElementById('totalPages'); 
  const show = document.getElementById('showingCount');
  const curB = document.getElementById('currentPageBottom'); 
  const totB = document.getElementById('totalPagesBottom');
  if (cur) cur.textContent = currentPage;
  if (tot) tot.textContent = totalPages;
  if (show) show.textContent = filteredData.length;
  const prev = document.getElementById('prevPage'); 
  const next = document.getElementById('nextPage');
  const prevB = document.getElementById('prevPageBottom'); 
  const nextB = document.getElementById('nextPageBottom');
  if (prev) prev.disabled = currentPage === 1;
  if (next) next.disabled = currentPage === totalPages;
  if (curB) curB.textContent = currentPage;
  if (totB) totB.textContent = totalPages;
  if (prevB) prevB.disabled = currentPage === 1;
  if (nextB) nextB.disabled = currentPage === totalPages;
}

function createQuestionCard(item) {
  const card = document.createElement('div'); 
  card.className = 'question-card';
  let personaText = item.group_prompt_template || '';
  if (item.group_prompt_variable_map) { 
    Object.entries(item.group_prompt_variable_map).forEach(([k, v]) => { 
      personaText = personaText.replace(`{${k}}`, v); 
    }); 
  }
  const klClass = item.kl_divergence < 0.1 ? 'good' : item.kl_divergence < 0.3 ? 'medium' : 'bad';
  card.innerHTML = `
    <div class="question-header">
      <div class="question-meta">
        <span class="meta-tag">${item.dataset_name || ''}</span>
        <span class="meta-tag">${item.Model || ''}</span>
        <span class="meta-tag">n=${item.group_size || 0}</span>
      </div>
      <div class="kl-badge ${klClass}">KL: ${item.kl_divergence.toFixed(3)}</div>
    </div>
    <div class="persona-text"><i class="fas fa-user-circle"></i> ${personaText}</div>
    <div class="question-text">${item.input_template || ''}</div>
    <div class="options-container" id="options-${item.index}">${renderOptions(item)}</div>
  `;
  return card;
}

function renderOptions(item) {
  const options = Object.keys(item.human_answer || {}).sort(); 
  let html = '';
  options.forEach(opt => {
    const h = (item.human_answer[opt] || 0) * 100; 
    const m = (item.Response_Distribution[opt] || 0) * 100;
    html += `
      <div class="option-item">
        <div class="option-label">Option ${opt}</div>
        <div class="distribution-bars">
          <div class="bar-container">
            <div class="bar-label">Human</div>
            <div class="bar-wrapper">
              <div class="bar-fill human" style="width: ${h}%">
                <span class="bar-text">${h.toFixed(1)}%</span>
              </div>
            </div>
          </div>
          <div class="bar-container">
            <div class="bar-label">Model</div>
            <div class="bar-wrapper">
              <div class="bar-fill model" style="width: ${m}%">
                <span class="bar-text">${m.toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  });
  return html;
}

function calculateKLDivergence(p, q) { 
  let kl = 0; 
  const eps = 1e-10; 
  Object.keys(p || {}).forEach(k => { 
    const pv = p[k] || 0; 
    const qv = q[k] || 0; 
    if (pv > 0) kl += pv * Math.log((pv + eps) / (qv + eps)); 
  }); 
  return Math.max(0, kl); 
}
