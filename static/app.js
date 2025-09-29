const state = {
  apiBase: localStorage.getItem('rla.apiBase') || '',
  caseId: null,
  lastCase: null,
  lastReasoning: null,
  lastIntake: null,
};

const configForm = document.getElementById('config-form');
const apiBaseInput = document.getElementById('api-base');
const alerts = document.getElementById('alerts');
const intakeForm = document.getElementById('intake-form');
const intakeOutput = document.getElementById('intake-output');
const casePanel = document.getElementById('case-panel');
const caseOutput = document.getElementById('case-output');
const caseStatus = document.getElementById('case-status');
const caseIdEl = document.getElementById('case-id');
const caseCategoryEl = document.getElementById('case-category');
const caseStageEl = document.getElementById('case-stage');
const caseDeadlineEl = document.getElementById('case-deadline');
const caseRisksEl = document.getElementById('case-risks');
const reasonBtn = document.getElementById('reason-btn');
const reasonExplanation = document.getElementById('reason-explanation');
const stepsList = document.getElementById('steps-list');
const deadlinesList = document.getElementById('deadlines-list');
const citationsList = document.getElementById('citations-list');
const draftForm = document.getElementById('draft-form');
const draftOutput = document.getElementById('draft-output');
const timelineList = document.getElementById('timeline-list');
const documentsList = document.getElementById('documents-list');
const escalateForm = document.getElementById('escalate-form');
const escalationOutput = document.getElementById('escalation-output');
const refreshBtn = document.getElementById('refresh-btn');
const lawSearchForm = document.getElementById('law-search-form');
const lawResults = document.getElementById('law-results');
const lawQueryInput = document.getElementById('law-query');
const lawTopkInput = document.getElementById('law-topk');

apiBaseInput.value = state.apiBase;

function setAlert(message, type = 'info') {
  if (!message) {
    alerts.textContent = '';
    alerts.removeAttribute('role');
    return;
  }
  alerts.textContent = message;
  alerts.setAttribute('role', type === 'error' ? 'alert' : 'status');
}

async function apiFetch(path, options = {}) {
  const base = state.apiBase ? state.apiBase.replace(/\/$/, '') : '';
  const url = `${base}${path}`;
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data && data.detail ? `: ${data.detail}` : '';
    throw new Error(`Request failed (${response.status})${detail}`);
  }
  return data;
}

function prettyPrint(target, data) {
  target.textContent = JSON.stringify(data, null, 2);
}

function ensureCaseLoaded() {
  if (!state.caseId) {
    setAlert('Create a case first.', 'error');
    return false;
  }
  return true;
}

function renderList(listEl, items, renderer) {
  listEl.innerHTML = '';
  if (!items || !items.length) {
    const li = document.createElement('li');
    li.textContent = 'No items yet.';
    listEl.appendChild(li);
    return;
  }
  items.forEach((item) => {
    const li = document.createElement('li');
    renderer(li, item);
    listEl.appendChild(li);
  });
}

function renderCase(casePayload) {
  if (!casePayload) return;
  state.lastCase = casePayload;
  caseStatus.textContent = 'Case active';
  caseIdEl.textContent = casePayload.case_id;
  caseCategoryEl.textContent = casePayload.category;
  caseStageEl.textContent = casePayload.status;
  caseDeadlineEl.textContent = casePayload.critical_deadline || '–';
  const risks =
    casePayload.risk_flags ||
    casePayload.facts?.risk_flags ||
    (state.lastIntake ? state.lastIntake.risk_flags : []);
  if (Array.isArray(risks) && risks.length) {
    caseRisksEl.innerHTML = '';
    const wrap = document.createElement('div');
    wrap.className = 'chips';
    risks.forEach((risk) => {
      const span = document.createElement('span');
      span.className = 'chip';
      span.textContent = risk;
      wrap.appendChild(span);
    });
    caseRisksEl.appendChild(wrap);
  } else {
    caseRisksEl.textContent = '–';
  }

  renderList(timelineList, casePayload.events, (node, event) => {
    const occurred = new Date(event.occurred_at).toLocaleString();
    const meta = Object.entries(event.metadata || {})
      .map(([key, value]) => `${key}: ${value}`)
      .join(', ');
    node.innerHTML = `<strong>${occurred}</strong> — ${event.label}${meta ? ` <small>(${meta})</small>` : ''}`;
  });

  renderList(documentsList, casePayload.documents, (node, doc) => {
    const link = document.createElement('a');
    link.href = doc.url;
    link.textContent = doc.filename;
    link.target = '_blank';
    const created = new Date(doc.created_at).toLocaleString();
    node.appendChild(link);
    const meta = document.createElement('div');
    meta.innerHTML = `<small>${doc.type} — ${created}</small>`;
    node.appendChild(meta);
  });

  renderList(citationsList, casePayload.law_citations, (node, citation) => {
    const link = document.createElement('a');
    link.href = citation.url;
    link.textContent = citation.point;
    link.target = '_blank';
    node.appendChild(link);
    const asOf = document.createElement('div');
    asOf.innerHTML = `<small>Current as of ${citation.as_of}</small>`;
    node.appendChild(asOf);
  });

  prettyPrint(caseOutput, casePayload);
  casePanel.hidden = false;
}

function renderReasoning(reasoning) {
  if (!reasoning) return;
  state.lastReasoning = reasoning;
  reasonExplanation.textContent = reasoning.explanation_plain;

  renderList(stepsList, reasoning.steps, (node, step, idx) => {
    node.textContent = step;
  });

  renderList(deadlinesList, reasoning.deadlines, (node, step) => {
    node.innerHTML = `<strong>${step.title || step.name || 'Deadline'}</strong> — ${step.description || ''} ${
      step.due_date ? `(due ${step.due_date})` : ''
    }`;
  });

  renderList(citationsList, reasoning.law_citations, (node, citation) => {
    const link = document.createElement('a');
    link.href = citation.url;
    link.textContent = citation.point;
    link.target = '_blank';
    node.appendChild(link);
    const asOf = document.createElement('div');
    asOf.innerHTML = `<small>Current as of ${citation.as_of}</small>`;
    node.appendChild(asOf);
  });
}

function renderDraft(draft) {
  if (!draft) return;
  const channel = Object.keys(draft.urls)[0];
  const url = draft.urls[channel];
  draftOutput.innerHTML = `Document ${draft.document_id} · <a href="${url}" target="_blank">Download ${channel.toUpperCase()}</a>`;
}

function renderEscalation(escalation) {
  if (!escalation) return;
  const list = [
    `<strong>Checklist</strong>`,
    `<ul>${escalation.checklist.map((item) => `<li>${item}</li>`).join('')}</ul>`,
    `<p><strong>Forms:</strong> ${escalation.forms_list.join(', ')}</p>`,
    `<p><a href="${escalation.fee_link}" target="_blank">VCAT fee guidance</a></p>`,
  ];
  if (escalation.draft_cover_letter_doc_id) {
    list.push(`<p>Cover letter draft ID: ${escalation.draft_cover_letter_doc_id}</p>`);
  }
  escalationOutput.innerHTML = list.join('\n');
}

async function loadCase() {
  if (!state.caseId) return;
  try {
    const casePayload = await apiFetch(`/api/case/${state.caseId}`);
    renderCase(casePayload);
    setAlert('Case refreshed.');
  } catch (error) {
    setAlert(error.message, 'error');
  }
}

configForm.addEventListener('submit', (event) => {
  event.preventDefault();
  state.apiBase = apiBaseInput.value.trim();
  localStorage.setItem('rla.apiBase', state.apiBase);
  setAlert(`API base set to ${state.apiBase || 'current origin'}.`);
});

intakeForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(intakeForm);
  const evidence = (formData.get('evidence_urls') || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
  const payload = {
    renter: { full_name: formData.get('renter_name') || '' },
    issue: formData.get('issue') || '',
    free_text: formData.get('free_text') || '',
    answers: {
      category: formData.get('issue_category') || '',
      first_reported: formData.get('first_reported') || '',
      subcategory: formData.get('subcategory') || '',
    },
    evidence_urls: evidence,
  };

  try {
    const data = await apiFetch('/api/intake', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    state.lastIntake = data;
    state.caseId = data.case_id;
    caseIdEl.textContent = data.case_id;
    caseStatus.textContent = 'Case created';
    caseCategoryEl.textContent = data.category;
    caseRisksEl.textContent = data.risk_flags?.join(', ') || '–';
    prettyPrint(intakeOutput, data);
    setAlert('Case created. Run the agents below.');
    await loadCase();
  } catch (error) {
    prettyPrint(intakeOutput, { error: error.message });
    setAlert(error.message, 'error');
  }
});

reasonBtn.addEventListener('click', async () => {
  if (!ensureCaseLoaded()) return;
  try {
    const reasoning = await apiFetch(`/api/case/${state.caseId}/reason`, { method: 'POST' });
    renderReasoning(reasoning);
    prettyPrint(document.getElementById('reason-output') || document.createElement('pre'), reasoning);
    setAlert('Reasoning generated.');
    await loadCase();
  } catch (error) {
    setAlert(error.message, 'error');
  }
});

draftForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!ensureCaseLoaded()) return;
  const formData = new FormData(draftForm);
  const payload = {
    template: formData.get('template'),
    channel: formData.get('channel'),
  };
  try {
    const draft = await apiFetch(`/api/case/${state.caseId}/draft`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    renderDraft(draft);
    setAlert('Draft generated.');
    await loadCase();
  } catch (error) {
    setAlert(error.message, 'error');
  }
});

escalateForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!ensureCaseLoaded()) return;
  const target = document.getElementById('escalate-target').value;
  try {
    const escalation = await apiFetch(`/api/case/${state.caseId}/escalate`, {
      method: 'POST',
      body: JSON.stringify({ target }),
    });
    renderEscalation(escalation);
    setAlert(`Escalation guidance prepared for ${target}.`);
    await loadCase();
  } catch (error) {
    setAlert(error.message, 'error');
  }
});

refreshBtn.addEventListener('click', async () => {
  if (!ensureCaseLoaded()) return;
  await loadCase();
});

lawSearchForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const query = lawQueryInput.value.trim();
    const topK = Number(lawTopkInput.value) || 3;
    const results = await apiFetch('/api/search-law', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    });
    const items = results.results || [];
    lawResults.innerHTML = '';
    if (!items.length) {
      const li = document.createElement('li');
      li.textContent = 'No results.';
      lawResults.appendChild(li);
    } else {
      items.forEach((result) => {
        const li = document.createElement('li');
        const article = document.createElement('article');
        const title = document.createElement('h3');
        title.textContent = result.title;
        const snippet = document.createElement('p');
        snippet.textContent = result.snippet;
        const link = document.createElement('a');
        link.href = result.source_url;
        link.target = '_blank';
        link.textContent = 'Open source';
        const asOf = document.createElement('small');
        asOf.textContent = `Current as of ${result.as_of_date}`;
        article.appendChild(title);
        article.appendChild(snippet);
        article.appendChild(link);
        article.appendChild(asOf);
        li.appendChild(article);
        lawResults.appendChild(li);
      });
    }
    setAlert('Law search complete.');
  } catch (error) {
    setAlert(error.message, 'error');
  }
});

if (state.apiBase) {
  setAlert(`Loaded API base from settings: ${state.apiBase}`);
}
