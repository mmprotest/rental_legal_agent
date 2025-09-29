const intakeForm = document.getElementById('intake-form');
const intakeOutput = document.getElementById('intake-output');
const reasonOutput = document.getElementById('reason-output');
const draftOutput = document.getElementById('draft-output');
const caseOutput = document.getElementById('case-output');
const caseActions = document.getElementById('case-actions');
const reasonBtn = document.getElementById('reason-btn');
const draftBtn = document.getElementById('draft-btn');
const refreshBtn = document.getElementById('refresh-btn');

let currentCaseId = null;

function prettyPrint(target, data) {
  target.textContent = JSON.stringify(data, null, 2);
}

function renderPlainAnswer(target, answer, citations) {
  const lines = [];
  if (answer) lines.push(answer);
  if (citations && citations.length) {
    lines.push('\nSources:');
    citations.forEach(c => {
      lines.push(`- ${c.point ? c.point + ' — ' : ''}${c.url}`);
    });
  }
  target.textContent = lines.join('\n');
}

async function handleIntake(event) {
  event.preventDefault();
  const formData = new FormData(intakeForm);
  const payload = {
    renter: { full_name: formData.get('renter_name') || '' },
    issue: formData.get('issue') || '',
    free_text: formData.get('free_text') || '',
    answers: {},
    evidence_urls: [],
  };
  const response = await fetch('/api/intake', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    prettyPrint(intakeOutput, data);
    return;
  }
  currentCaseId = data.case_id;
  prettyPrint(intakeOutput, data);
  caseActions.hidden = false;
}

async function runReasoner() {
  if (!currentCaseId) return;
  const response = await fetch(`/api/case/${currentCaseId}/reason`, { method: 'POST' });
  const data = await response.json();
  renderPlainAnswer(reasonOutput, data.explanation_plain, data.law_citations);
}

async function draftLetter() {
  if (!currentCaseId) return;
  const response = await fetch(`/api/case/${currentCaseId}/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template: 'repairs_urgent', channel: 'docx' }),
  });
  const data = await response.json();
  const subject = data.preview_subject || '(no subject)';
  const body = data.preview_body || '(no body)';
  draftOutput.textContent = `${subject}\n\n${body}\n\nDownload: ${data.urls.docx}`;
}

async function refreshCase() {
  if (!currentCaseId) return;
  const response = await fetch(`/api/case/${currentCaseId}`);
  const data = await response.json();
  prettyPrint(caseOutput, data);
}

intakeForm.addEventListener('submit', handleIntake);
reasonBtn.addEventListener('click', runReasoner);
draftBtn.addEventListener('click', draftLetter);
refreshBtn.addEventListener('click', refreshCase);

// Chat-style Ask UI
const askForm = document.createElement('form');
askForm.id = 'ask-form';
askForm.innerHTML = `
  <h2>Ask a legal question</h2>
  <label>
    Your question
    <textarea name="question" rows="3" placeholder="e.g., Is no hot water an urgent repair in Victoria?"></textarea>
  </label>
  <button type="submit">Ask</button>
  <pre id="ask-output" class="output"></pre>
`;
document.querySelector('main.container').appendChild(askForm);
const askOutput = askForm.querySelector('#ask-output');
askForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = new FormData(askForm);
  const question = form.get('question') || '';
  const res = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }) });
  const ans = await res.json();
  renderPlainAnswer(askOutput, ans.answer, ans.citations);
});
