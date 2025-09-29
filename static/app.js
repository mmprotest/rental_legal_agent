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
  prettyPrint(reasonOutput, data);
}

async function draftLetter() {
  if (!currentCaseId) return;
  const response = await fetch(`/api/case/${currentCaseId}/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template: 'repairs_urgent', channel: 'docx' }),
  });
  const data = await response.json();
  prettyPrint(draftOutput, data);
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
