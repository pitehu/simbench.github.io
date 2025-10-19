"use strict";

// SimBench Results Explorer - Version 2 with enhanced filtering and display

let allData = [];
let filteredData = [];
let currentPage = 1;
let itemsPerPage = 25;
let availableModels = [];
let availableSubsets = [];

document.addEventListener('DOMContentLoaded', () => {
  initializeControls();
  initializeExampleLoading();
});

function initializeExampleLoading() {
  // Auto-load real_results_visualization.json on page load
  console.log('Auto-loading real_results_visualization.json...');
  
  const loadingIndicator = document.getElementById('loadingIndicator');
  if (loadingIndicator) loadingIndicator.style.display = 'block';
  
  fetch('data/real_results_visualization.json')
    .then(resp => {
      if (!resp.ok) throw new Error('File not found');
      return resp.json();
    })
    .then(data => {
      if (loadingIndicator) loadingIndicator.style.display = 'none';
      displayResults(data);
    })
    .catch(e => {
      console.error('Could not load real_results_visualization.json:', e);
      if (loadingIndicator) loadingIndicator.style.display = 'none';
      // Fallback to sample data
      displayResults(generateSampleData());
    });
}

function generateSampleData() {
  const datasets = ['OpinionQA', 'WisdomOfCrowds', 'ChaosNLI', 'MoralMachine', 'BIG5', 'ESS'];
  const models = ['GPT-4.1', 'Claude-3.5', 'Llama-3-70b', 'Gemini-Pro'];
  const subsets = ['SimBenchPop', 'SimBenchGrouped'];
  const countries = ['United States', 'Kenya', 'Germany', 'Brazil', 'Japan', 'India'];
  const data = [];
  
  for (let i = 0; i < 200; i++) {
    const numOpts = [2, 3, 4, 5][Math.floor(Math.random() * 4)];
    const options = ['A', 'B', 'C', 'D', 'E'].slice(0, numOpts);
    
    // Generate answer option texts
    const answerTexts = options.map((o, idx) => 
      ['flimsy', 'kindle', 'suffrage', 'maze', 'improve'][idx % 5]
    );
    
    // Generate human distribution with some entropy
    let remaining = 1.0;
    const human = {};
    for (let j = 0; j < options.length; j++) {
      if (j === options.length - 1) {
        human[options[j]] = remaining;
      } else {
        const v = Math.random() * remaining * 0.6;
        human[options[j]] = v;
        remaining -= v;
      }
    }
    const hsum = Object.values(human).reduce((a, b) => a + b, 0);
    Object.keys(human).forEach(k => human[k] /= hsum);
    
    // Calculate entropy
    const entropy = -Object.values(human).reduce((sum, p) => {
      return p > 0 ? sum + p * Math.log(p) : sum;
    }, 0) / Math.log(numOpts);
    
    // Generate model distribution (correlated with human)
    const model = {};
    const corr = 0.5 + Math.random() * 0.5;
    Object.keys(human).forEach(k => {
      model[k] = Math.max(0.001, human[k] * corr + (1 - corr) * (1 / options.length) * Math.random());
    });
    const msum = Object.values(model).reduce((a, b) => a + b, 0);
    Object.keys(model).forEach(k => model[k] /= msum);
    
    // Generate SimBench Score (higher is better, range -inf to 100)
    const simBenchScore = 100 - Math.abs(calculateKLDivergence(human, model)) * 50;
    
    const subset = subsets[Math.floor(Math.random() * subsets.length)];
    const systemPrompt = subset === 'SimBenchGrouped' 
      ? `You are a group of individuals with these shared characteristics:\nYou are from ${countries[Math.floor(Math.random() * countries.length)]}.`
      : 'You are an Amazon Mechanical Turk worker from the United States.';

    data.push({
      dataset_name: datasets[Math.floor(Math.random() * datasets.length)],
      input_template: `Sample question ${i + 1}: An analogy compares the relationship between two things or ideas to highlight some point of similarity. Which pair of words has the same relationship?\n\nOptions:\n${options.map((o, idx) => `(${o}): ${answerTexts[idx]}`).join('\n')}`,
      System_Prompt: systemPrompt,
      Subset: subset,
      Human_Normalized_Entropy: entropy,
      Human_Agreement: entropy < 0.33 ? 'High' : entropy < 0.66 ? 'Medium' : 'Low',
      human_answer: human,
      Response_Distribution: model,
      Model: models[Math.floor(Math.random() * models.length)],
      SimBench_Score: simBenchScore,
      group_size: Math.floor(100 + Math.random() * 1000),
      answer_options: answerTexts
    });
  }
  return data;
}

function displayResults(data) {
  console.time('displayResults');
  
  // OPTIMIZATION: Group data by unique questions first
  const questionMap = new Map();
  
  data.forEach((item, idx) => {
    // Create unique question identifier
    const questionKey = `${item.input_template || ''}|||${item.System_Prompt || ''}|||${item.dataset_name || ''}`;
    
    if (!questionMap.has(questionKey)) {
      questionMap.set(questionKey, {
        question: item.input_template || 'No question text',
        system_prompt: item.System_Prompt || '',
        dataset_name: item.dataset_name || 'Unknown',
        Subset: item.Subset || '',
        human_answer: item.human_answer || {},
        answer_options: item.answer_options || [],
        Human_Normalized_Entropy: item.Human_Normalized_Entropy,
        Human_Agreement: item.Human_Agreement || 'Unknown',
        models: []
      });
    }
    
    // Add this model's response to the question
    questionMap.get(questionKey).models.push({
      Model: item.Model || 'Unknown',
      Response_Distribution: item.Response_Distribution || {},
      SimBench_Score: item.SimBench_Score != null ? item.SimBench_Score : 0,
      kl_divergence: calculateKLDivergence(item.human_answer || {}, item.Response_Distribution || {}),
      original_index: idx
    });
  });
  
  // Convert to array and sort models within each question
  allData = Array.from(questionMap.values()).map(q => {
    q.models.sort((a, b) => a.Model.localeCompare(b.Model));
    return q;
  });
  
  filteredData = [...allData];
  availableModels = [...new Set(data.map(d => d.Model).filter(Boolean))].sort();
  availableSubsets = [...new Set(data.map(d => d.Subset).filter(Boolean))].sort();
  
  console.timeEnd('displayResults');
  
  updateSummaryStats();
  populateFilters();
  
  const rs = document.getElementById('resultsSection');
  if (rs) rs.style.display = 'block';
  
  currentPage = 1;
  applySorting();
}

function updateSummaryStats() {
  const statDataset = document.getElementById('statDataset');
  const statModel = document.getElementById('statModel');
  const statQuestions = document.getElementById('statQuestions');
  const statAvgKL = document.getElementById('statAvgKL');
  
  const datasets = [...new Set(allData.map(d => d.dataset_name))];
  const totalModels = availableModels.length;
  const avgScore = allData.length ? 
    allData.reduce((sum, q) => sum + q.models.reduce((s, m) => s + m.SimBench_Score, 0) / q.models.length, 0) / allData.length : 0;
  
  if (statDataset) statDataset.textContent = datasets.length > 1 ? `${datasets.length} datasets` : (datasets[0] || '-');
  if (statModel) statModel.textContent = `${totalModels} models`;
  if (statQuestions) statQuestions.textContent = allData.length;
  if (statAvgKL) statAvgKL.textContent = avgScore.toFixed(1);
}

function populateFilters() {
  console.time('populateFilters');
  
  const datasets = [...new Set(allData.map(d => d.dataset_name))].sort();
  const datasetFilter = document.getElementById('datasetFilter');
  const subsetFilter = document.getElementById('subsetFilter');
  
  if (!datasetFilter) return;
  
  // Populate dataset filter
  datasetFilter.innerHTML = '<option value="all">All Datasets</option>';
  datasets.forEach(ds => {
    const o = document.createElement('option');
    o.value = ds;
    o.textContent = ds;
    datasetFilter.appendChild(o);
  });
  
  // Populate subset filter
  if (subsetFilter) {
    subsetFilter.innerHTML = '<option value="all">All Subsets</option>';
    availableSubsets.forEach(s => {
      const o = document.createElement('option');
      o.value = s;
      o.textContent = s;
      subsetFilter.appendChild(o);
    });
  }
  
  // Populate model checkboxes
  populateModelCheckboxes();
  
  console.timeEnd('populateFilters');
}

function populateModelCheckboxes() {
  const container = document.getElementById('modelCheckboxes');
  if (!container) return;
  
  container.innerHTML = '';
  
  availableModels.forEach(model => {
    const item = document.createElement('div');
    item.className = 'model-checkbox-item';
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = `model-${model.replace(/[^a-zA-Z0-9]/g, '_')}`;
    checkbox.value = model;
    // Only select Claude-3.7-Sonnet by default
    checkbox.checked = model.includes('Claude') && model.includes('3.7') && model.includes('Sonnet');
    checkbox.addEventListener('change', renderQuestions);
    
    const label = document.createElement('label');
    label.htmlFor = checkbox.id;
    label.textContent = model;
    
    item.appendChild(checkbox);
    item.appendChild(label);
    
    // Make clicking the item toggle the checkbox
    item.addEventListener('click', (e) => {
      if (e.target !== checkbox) {
        checkbox.checked = !checkbox.checked;
        renderQuestions();
      }
    });
    
    container.appendChild(item);
  });
  
  // Add select/deselect all button handlers
  const selectAll = document.getElementById('selectAllModels');
  const deselectAll = document.getElementById('deselectAllModels');
  
  if (selectAll) {
    selectAll.onclick = () => {
      container.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = true);
      renderQuestions();
    };
  }
  
  if (deselectAll) {
    deselectAll.onclick = () => {
      container.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
      renderQuestions();
    };
  }
}

function getSelectedModels() {
  const checkboxes = document.querySelectorAll('#modelCheckboxes input[type="checkbox"]:checked');
  return Array.from(checkboxes).map(cb => cb.value);
}

function initializeControls() {
  // Filter controls
  const df = document.getElementById('datasetFilter');
  if (df) df.addEventListener('change', applyFilters);
  
  const sf = document.getElementById('subsetFilter');
  if (sf) sf.addEventListener('change', applyFilters);
  
  const af = document.getElementById('agreementFilter');
  if (af) af.addEventListener('change', applyFilters);
  
  const si = document.getElementById('searchInput');
  if (si) si.addEventListener('input', applyFilters);
  
  // Sorting control
  const ss = document.getElementById('sortSelect');
  if (ss) ss.addEventListener('change', applySorting);
  
  // Pagination controls
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
  
  // Bottom pagination if exists
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
  const subsetVal = (document.getElementById('subsetFilter') || {}).value || 'all';
  const agreementVal = (document.getElementById('agreementFilter') || {}).value || 'all';
  const searchTerm = ((document.getElementById('searchInput') || {}).value || '').toLowerCase();
  
  filteredData = allData.filter(item => {
    const okDataset = datasetVal === 'all' || item.dataset_name === datasetVal;
    const okSubset = subsetVal === 'all' || (item.Subset && item.Subset === subsetVal);
    const okAgreement = agreementVal === 'all' || (item.Human_Agreement && item.Human_Agreement === agreementVal);
    const okSearch = !searchTerm || (item.question || '').toLowerCase().includes(searchTerm);
    return okDataset && okSubset && okAgreement && okSearch;
  });
  
  currentPage = 1;
  applySorting();
}

function applySorting() {
  console.time('applySorting');
  const sortBy = (document.getElementById('sortSelect') || {}).value || 'score-desc';
  
  switch (sortBy) {
    case 'score-asc':
      filteredData.sort((a, b) => {
        const avgA = a.models.length ? a.models.reduce((s, m) => s + m.SimBench_Score, 0) / a.models.length : 0;
        const avgB = b.models.length ? b.models.reduce((s, m) => s + m.SimBench_Score, 0) / b.models.length : 0;
        return avgA - avgB;
      });
      break;
    case 'score-desc':
      filteredData.sort((a, b) => {
        const avgA = a.models.length ? a.models.reduce((s, m) => s + m.SimBench_Score, 0) / a.models.length : 0;
        const avgB = b.models.length ? b.models.reduce((s, m) => s + m.SimBench_Score, 0) / b.models.length : 0;
        return avgB - avgA;
      });
      break;
    case 'entropy-asc':
      filteredData.sort((a, b) => (a.Human_Normalized_Entropy || 0) - (b.Human_Normalized_Entropy || 0));
      break;
    case 'entropy-desc':
      filteredData.sort((a, b) => (b.Human_Normalized_Entropy || 0) - (a.Human_Normalized_Entropy || 0));
      break;
    case 'dataset':
      filteredData.sort((a, b) => (a.dataset_name || '').localeCompare(b.dataset_name || ''));
      break;
    case 'index':
    default:
      // Keep current order
      break;
  }
  
  console.timeEnd('applySorting');
  renderQuestions();
}

function renderQuestions() {
  console.time('renderQuestions');
  const container = document.getElementById('questionsContainer');
  if (!container) return;
  
  // Get selected models
  const selectedModels = getSelectedModels();
  if (selectedModels.length === 0) {
    container.innerHTML = '<div class="no-results"><p>Please select at least one model to display.</p></div>';
    updatePaginationControls(0);
    console.timeEnd('renderQuestions');
    return;
  }
  
  container.innerHTML = '';
  const totalPages = Math.max(1, Math.ceil(filteredData.length / itemsPerPage));
  const startIdx = (currentPage - 1) * itemsPerPage;
  const endIdx = Math.min(startIdx + itemsPerPage, filteredData.length);
  const pageData = filteredData.slice(startIdx, endIdx);
  
  // Use DocumentFragment for better performance
  const fragment = document.createDocumentFragment();
  pageData.forEach(item => {
    fragment.appendChild(createQuestionCard(item, selectedModels));
  });
  container.appendChild(fragment);
  
  updatePaginationControls(totalPages);
  window.scrollTo({ top: 0, behavior: 'smooth' });
  console.timeEnd('renderQuestions');
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

function createQuestionCard(item, selectedModels) {
  const card = document.createElement('div');
  card.className = 'question-card';
  
  // Filter models to only show selected ones
  const modelsToShow = item.models.filter(m => selectedModels.includes(m.Model));
  if (modelsToShow.length === 0) return card;
  
  // Determine entropy color
  const entropy = item.Human_Normalized_Entropy != null ? item.Human_Normalized_Entropy : 1;
  const entropyClass = entropy < 0.33 ? 'good' : entropy < 0.66 ? 'medium' : 'bad';
  
  // Separate question text from options
  let questionText = item.question || 'No question text';
  let optionsText = '';
  
  // Try to split at "Options:" marker
  const optionsIndex = questionText.indexOf('Options:');
  if (optionsIndex !== -1) {
    optionsText = questionText.substring(optionsIndex);
    questionText = questionText.substring(0, optionsIndex).trim();
  }
  
  // Build card HTML
  let html = `
    <div class="question-header">
      <div class="question-meta">
        <span class="meta-tag"><i class="fas fa-database"></i> ${escapeHtml(item.dataset_name || 'Unknown')}</span>
        <span class="meta-tag"><i class="fas fa-layer-group"></i> ${escapeHtml(item.Subset || 'Unknown')}</span>
      </div>
      <div class="question-badges">
        <div class="kl-badge ${entropyClass}" title="Human Response Entropy (lower = more consensus)">
          Entropy: ${entropy.toFixed(2)}
        </div>
      </div>
    </div>
  `;
  
  // System Prompt
  if (item.system_prompt) {
    html += `
    <div class="system-prompt-box">
      <div class="system-prompt-header"><i class="fas fa-cog"></i> System Prompt</div>
      <div class="system-prompt-text">${escapeHtml(item.system_prompt)}</div>
    </div>
    `;
  }
  
  // Question text (without options)
  html += `<div class="question-text">${escapeHtml(questionText)}</div>`;
  
  // Get options with their text labels
  const options = Object.keys(item.human_answer || {}).sort();
  const answerTexts = item.answer_options || [];
  
  // Response visualization - redesigned for better multi-model support
  html += `<div class="response-visualization">`;
  
  // Show model scores in a summary row at the top
  if (modelsToShow.length > 0) {
    html += `
      <div class="model-scores-summary">
        <div class="score-label"><strong>SimBench Scores:</strong></div>
        <div class="score-list">
    `;
    
    modelsToShow.forEach(model => {
      html += `
        <span class="model-score-chip">
          <span class="model-name-short">${escapeHtml(model.Model)}</span>
          <span class="score-value">${model.SimBench_Score.toFixed(1)}</span>
        </span>
      `;
    });
    
    html += `</div></div>`; // Close model-scores-summary
  }
  
  // Table header
  html += `
    <table class="response-table">
      <thead>
        <tr>
          <th class="option-col">Option</th>
          <th class="response-col human-col">
            <i class="fas fa-users"></i> Human
          </th>
  `;
  
  modelsToShow.forEach(model => {
    html += `
      <th class="response-col model-col">
        <i class="fas fa-robot"></i> ${escapeHtml(model.Model)}
      </th>
    `;
  });
  
  html += `
        </tr>
      </thead>
      <tbody>
  `;
  
  // Response rows - one per option
  options.forEach(opt => {
    // Get option text
    let optionText = opt;
    if (answerTexts && answerTexts.length > 0) {
      const optIndex = opt.charCodeAt(0) >= 65 && opt.charCodeAt(0) <= 90 
        ? opt.charCodeAt(0) - 65 
        : parseInt(opt);
      
      if (optIndex >= 0 && optIndex < answerTexts.length) {
        optionText = answerTexts[optIndex];
      }
    }
    
    html += `
      <tr>
        <td class="option-cell">
          <span class="option-letter">${opt}</span>
          <span class="option-text">${escapeHtml(optionText)}</span>
        </td>
    `;
    
    // Human response
    const humanProb = (item.human_answer[opt] || 0) * 100;
    html += `
      <td class="response-cell human-cell">
        <div class="bar-container">
          <div class="response-bar human-bar" style="width: ${humanProb}%"></div>
          <span class="percentage-label">${humanProb.toFixed(1)}%</span>
        </div>
      </td>
    `;
    
    // Model responses
    modelsToShow.forEach(model => {
      const modelProb = (model.Response_Distribution[opt] || 0) * 100;
      
      html += `
        <td class="response-cell model-cell">
          <div class="bar-container">
            <div class="response-bar model-bar" style="width: ${modelProb}%"></div>
            <span class="percentage-label">${modelProb.toFixed(1)}%</span>
          </div>
        </td>
      `;
    });
    
    html += `</tr>`;
  });
  
  html += `
      </tbody>
    </table>
  `; // Close table
  
  html += `</div>`; // Close response-visualization
  
  card.innerHTML = html;
  return card;
}

function calculateKLDivergence(p, q) {
  let kl = 0;
  const eps = 1e-10;
  Object.keys(p || {}).forEach(k => {
    const pv = p[k] || 0;
    const qv = q[k] || 0;
    if (pv > 0) {
      kl += pv * Math.log((pv + eps) / (qv + eps));
    }
  });
  return Math.max(0, kl);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
