// S.I.A. (Smart Insurance Assistant) Frontend Orchestrator

const API_BASE = window.location.origin.startsWith('file') || window.location.origin === 'null' 
  ? 'http://localhost:8000' 
  : window.location.origin;

let scenarios = [];
let policies = {};
let activeClaim = null;

// Selectors
const scenarioSelect = document.getElementById('scenario-select');
const policySelect = document.getElementById('policy-select');
const billTextarea = document.getElementById('bill-text');
const dischargeTextarea = document.getElementById('discharge-text');
const runBtn = document.getElementById('run-btn');

// Summary Selectors
const summaryPlaceholder = document.getElementById('summary-placeholder');
const summaryResults = document.getElementById('summary-results');
const displayCaseId = document.getElementById('display-case-id');
const displayPatientName = document.getElementById('display-patient-name');
const displayStatus = document.getElementById('display-status');
const displayAbha = document.getElementById('display-abha');
const displayAadhaar = document.getElementById('display-aadhaar');
const displayInsurer = document.getElementById('display-insurer');
const displayHospital = document.getElementById('display-hospital');
const displayDoctor = document.getElementById('display-doctor');
const displayProcedure = document.getElementById('display-procedure');

const displayGross = document.getElementById('display-gross');
const displayDeductions = document.getElementById('display-deductions');
const displayCopay = document.getElementById('display-copay');
const displayPayout = document.getElementById('display-payout');
const displayBreakdownBody = document.getElementById('display-breakdown-body');

const displayChecklistStatus = document.getElementById('display-checklist-status');
const displayVerifiedDocs = document.getElementById('display-verified-docs');
const displayMissingDocsBox = document.getElementById('display-missing-docs-box');
const displayMissingDocsList = document.getElementById('display-missing-docs-list');

const displayDaysRemaining = document.getElementById('display-days-remaining');
const displayOmbudsman = document.getElementById('display-ombudsman');
const displayReminderChips = document.getElementById('display-reminder-chips');

const displayEmailDraftBox = document.getElementById('display-email-draft-box');
const displayEmailDraft = document.getElementById('display-email-draft');
const copyEmailBtn = document.getElementById('copy-email-btn');

const downloadPdfBtn = document.getElementById('download-pdf-btn');
const copyJsonBtn = document.getElementById('copy-json-btn');
const jsonOutput = document.getElementById('json-output');
const auditLogBody = document.getElementById('audit-log-body');

// Launch Initialization
document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  fetchPolicies();
  fetchSampleCases();
  
  // Event listeners
  scenarioSelect.addEventListener('change', loadSelectedScenario);
  runBtn.addEventListener('click', runAdjudicationLoop);
  copyEmailBtn.addEventListener('click', copyEmailToClipboard);
  copyJsonBtn.addEventListener('click', copyJsonToClipboard);
});

// Setup tab navigation switches
function setupTabs() {
  // Editor Tabs
  const editorTabs = document.querySelectorAll('.editor-tab');
  editorTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      editorTabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.editor-content').forEach(c => c.classList.remove('active'));
      
      tab.classList.add('active');
      const targetId = tab.getAttribute('data-tab');
      document.getElementById(targetId).classList.add('active');
    });
  });

  // Results Tabs
  const resultsTabs = document.querySelectorAll('.results-tab');
  resultsTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      resultsTabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.results-tab-content').forEach(c => c.classList.remove('active'));
      
      tab.classList.add('active');
      const targetId = tab.getAttribute('data-tab');
      document.getElementById(targetId).classList.add('active');
    });
  });
}

// Fetch Predefined Policies
async function fetchPolicies() {
  try {
    const res = await fetch(`${API_BASE}/api/policies`);
    policies = await res.json();
    
    // Populate select
    policySelect.innerHTML = '<option value="" disabled selected>Select insurance policy...</option>';
    Object.keys(policies).forEach(key => {
      const option = document.createElement('option');
      option.value = key;
      option.textContent = `${policies[key].insurer} (${key})`;
      policySelect.appendChild(option);
    });
  } catch (err) {
    console.error('Failed to fetch policies:', err);
    policySelect.innerHTML = '<option value="" disabled>Error loading policies</option>';
  }
}

// Fetch Sample Cases
async function fetchSampleCases() {
  try {
    const res = await fetch(`${API_BASE}/api/sample-cases`);
    scenarios = await res.json();
    
    scenarioSelect.innerHTML = '<option value="" disabled selected>Select claim scenario...</option>';
    scenarios.forEach(sc => {
      const option = document.createElement('option');
      option.value = sc.id;
      option.textContent = sc.name;
      scenarioSelect.appendChild(option);
    });
  } catch (err) {
    console.error('Failed to fetch sample cases:', err);
    scenarioSelect.innerHTML = '<option value="" disabled>Error loading scenarios</option>';
  }
}

// Preload Selected Scenario
function loadSelectedScenario() {
  const selectedId = scenarioSelect.value;
  const scenario = scenarios.find(sc => sc.id === selectedId);
  if (!scenario) return;

  billTextarea.value = scenario.hospital_bill;
  dischargeTextarea.value = scenario.discharge_summary;
  
  // Set matching policy
  policySelect.value = scenario.policy_number;
}

// Copy utilities
function copyEmailToClipboard() {
  navigator.clipboard.writeText(displayEmailDraft.textContent);
  copyEmailBtn.textContent = 'Copied!';
  setTimeout(() => { copyEmailBtn.textContent = 'Copy Email Text'; }, 2000);
}

function copyJsonToClipboard() {
  navigator.clipboard.writeText(jsonOutput.textContent);
  copyJsonBtn.textContent = 'Copied!';
  setTimeout(() => { copyJsonBtn.textContent = 'Copy JSON'; }, 2000);
}

// Animated 6-Agent loop orchestrator
async function runAdjudicationLoop() {
  const billText = billTextarea.value.trim();
  const dischargeText = dischargeTextarea.value.trim();
  const policyNum = policySelect.value;

  if (!billText || !dischargeText || !policyNum) {
    alert('Please fill out the Hospital Bill, Discharge Summary, and select a Target Policy.');
    return;
  }

  // Reset UI components for fresh run
  summaryPlaceholder.style.display = 'flex';
  summaryResults.style.display = 'none';
  displayEmailDraftBox.style.display = 'none';
  displayMissingDocsBox.style.display = 'none';
  jsonOutput.textContent = '{ "status": "Processing loop..." }';
  
  // Clear logs body
  auditLogBody.innerHTML = '<p class="term-line opacity-50">&gt;&gt; Initialize S.I.A. Multi-Agent Kernel...</p>';
  
  // Reset Progress Rail
  const steps = [1, 2, 3, 4, 5, 6, 7];
  steps.forEach(i => {
    const el = document.getElementById(`step-${i}`);
    el.classList.remove('active', 'complete');
  });
  document.getElementById('progress-line').style.width = '0%';
  
  // Show terminal tab during active runs
  document.querySelector('.results-tab[data-tab="tab-audit"]').click();

  // Call API in background
  let apiResponse = null;
  let apiError = null;
  
  const apiCallPromise = fetch(`${API_BASE}/api/adjudicate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      hospital_bill: billText,
      discharge_summary: dischargeText,
      policy_number: policyNum
    })
  })
  .then(res => {
    if (!res.ok) throw new Error('API server returned error during adjudication');
    return res.json();
  })
  .then(data => { apiResponse = data; })
  .catch(err => { apiError = err; });

  // Sequentially animate the steps on screen
  const stepDelays = 900; // ms
  
  const stepLogs = [
    { num: 1, agent: 'IntakeAgent', action: 'Triggering multimodal text ingestion and parsing...' },
    { num: 2, agent: 'SafetyAgent', action: 'Initiating PII sanitization (DPDP compliance check) & registry check...' },
    { num: 3, agent: 'EligibilityAgent', action: 'Loading policy contracts. Computing deductible line-item variables...' },
    { num: 4, agent: 'EvidenceAgent', action: 'Analyzing clinical alignment between bill codes and summary notes...' },
    { num: 5, agent: 'PackageAgent', action: 'Formatting standardized IRDAI claim form package fields...' },
    { num: 6, agent: 'SlaAgent', action: 'Calculating elapsed timeline metrics and statutory dates...' },
    { num: 7, agent: 'ReflectionAgent', action: 'Initiating verification loop (math checksums & float formatting)...' }
  ];

  for (let idx = 0; idx < stepLogs.length; idx++) {
    const step = stepLogs[idx];
    
    // Highlight step as Active
    const stepEl = document.getElementById(`step-${step.num}`);
    stepEl.classList.add('active');
    
    // Fill progress line
    const progressPercent = ((step.num - 1) / 6) * 100;
    document.getElementById('progress-line').style.width = `${progressPercent}%`;

    // Append log line
    appendLogLine(step.agent, step.action);
    
    // Wait for delay
    await new Promise(r => setTimeout(r, stepDelays));
    
    // Mark step as completed
    stepEl.classList.remove('active');
    stepEl.classList.add('complete');
  }
  
  // Set progress fill to 100%
  document.getElementById('progress-line').style.width = '100%';

  // Await API completion if it hasn't resolved yet
  appendLogLine('SystemKernel', 'Awaiting API database persistence thread...');
  while (!apiResponse && !apiError) {
    await new Promise(r => setTimeout(r, 100));
  }

  if (apiError) {
    appendLogLine('SystemError', `Adjudication Loop Halted: ${apiError.message}`);
    jsonOutput.textContent = JSON.stringify({ error: apiError.message }, null, 2);
    alert('Adjudication Loop failed. Check backend console.');
    return;
  }

  // Adjudication finished successfully, display outputs
  activeClaim = apiResponse;
  renderAdjudicationResults(activeClaim);
}

// Append log line helper
function appendLogLine(agent, action) {
  const line = document.createElement('p');
  line.className = 'term-line';
  
  const timeSpan = document.createElement('span');
  timeSpan.className = 'time';
  timeSpan.textContent = `[${new Date().toLocaleTimeString()}]`;
  
  const agentSpan = document.createElement('span');
  agentSpan.className = 'agent';
  agentSpan.textContent = `[${agent}] `;
  
  const actionSpan = document.createElement('span');
  actionSpan.className = 'action';
  actionSpan.textContent = action;
  
  line.appendChild(timeSpan);
  line.appendChild(agentSpan);
  line.appendChild(actionSpan);
  
  auditLogBody.appendChild(line);
  auditLogBody.scrollTop = auditLogBody.scrollHeight;
}

// Render Results on screen
function renderAdjudicationResults(claim) {
  // Switch to Summary Tab
  document.querySelector('.results-tab[data-tab="tab-summary"]').click();
  
  summaryPlaceholder.style.display = 'none';
  summaryResults.style.display = 'flex';
  
  // Meta Info
  displayCaseId.textContent = claim.claim_case_id;
  displayPatientName.textContent = claim.patient_profile.patient_name;
  
  // Status Class
  displayStatus.textContent = claim.status;
  displayStatus.className = 'case-status-badge'; // reset
  if (claim.status === 'READY_FOR_APPROVAL') {
    displayStatus.classList.add('ready');
  } else {
    displayStatus.classList.add('escalated');
  }
  
  // Demographics
  displayAbha.textContent = claim.patient_profile.abha_id;
  displayAadhaar.textContent = claim.patient_profile.aadhaar_masked;
  displayInsurer.textContent = claim.patient_profile.insurer_name;
  
  // Clinicals
  displayHospital.textContent = claim.clinical_summary.hospital_name;
  displayDoctor.textContent = `${claim.clinical_summary.treating_doctor} (${claim.clinical_summary.doctor_verified ? 'Verified NMC' : 'Unverified SMC'})`;
  displayProcedure.textContent = claim.clinical_summary.procedure_performed;
  
  // Financials
  const fin = claim.financial_adjudication;
  displayGross.textContent = `INR ${fin.gross_claimed_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
  displayDeductions.textContent = `INR ${fin.non_medical_deductions.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
  displayCopay.textContent = `INR ${fin.copay_deduction_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
  displayPayout.textContent = `INR ${fin.net_approved_payout.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
  
  // Table Breakdown
  displayBreakdownBody.innerHTML = '';
  fin.itemized_breakdown.forEach(item => {
    const tr = document.createElement('tr');
    
    const tdCat = document.createElement('td');
    tdCat.textContent = item.category;
    
    const tdBilled = document.createElement('td');
    tdBilled.className = 'num';
    tdBilled.textContent = item.billed.toLocaleString(undefined, {minimumFractionDigits: 2});
    
    const tdApp = document.createElement('td');
    tdApp.className = 'num';
    tdApp.textContent = item.payable.toLocaleString(undefined, {minimumFractionDigits: 2});
    
    const tdReason = document.createElement('td');
    tdReason.textContent = item.deduction_reason;
    if (item.payable < item.billed) {
      tdReason.classList.add('warning-text');
    }
    
    tr.appendChild(tdCat);
    tr.appendChild(tdBilled);
    tr.appendChild(tdApp);
    tr.appendChild(tdReason);
    
    displayBreakdownBody.appendChild(tr);
  });
  
  // Evidence Card
  const ev = claim.evidence_audit;
  displayChecklistStatus.textContent = ev.checklist_status;
  displayVerifiedDocs.textContent = ev.documents_verified.join(', ');
  
  // Missing docs
  if (ev.missing_documents && ev.missing_documents.length > 0) {
    displayMissingDocsBox.style.display = 'block';
    displayMissingDocsList.innerHTML = '';
    ev.missing_documents.forEach(doc => {
      const li = document.createElement('li');
      li.textContent = doc.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      displayMissingDocsList.appendChild(li);
    });
  } else {
    displayMissingDocsBox.style.display = 'none';
  }
  
  // SLA Statutory Compliance
  const stat = claim.statutory_compliance;
  const daysRem = stat.days_remaining_to_file;
  displayDaysRemaining.textContent = daysRem >= 0 ? `${daysRem} Days Remaining` : `Exceeded by ${Math.abs(daysRem)} Days`;
  if (daysRem < 0) displayDaysRemaining.classList.add('warning-text');
  else displayDaysRemaining.classList.remove('warning-text');
  
  displayOmbudsman.textContent = stat.ombudsman_appeal_ready ? 'ELIGIBLE' : 'NOT APPLICABLE';
  if (stat.ombudsman_appeal_ready) displayOmbudsman.classList.add('warning-text');
  else displayOmbudsman.classList.remove('warning-text');
  
  // Populate reminder schedule
  displayReminderChips.innerHTML = '';
  // Load target dates dynamically from logs/reminders if available
  const currentDischargeDate = claim.clinical_summary.discharge_date;
  if (currentDischargeDate) {
    const dDate = new Date(currentDischargeDate);
    const day7 = new Date(dDate.setDate(dDate.getDate() + 7)).toLocaleDateString();
    const day15 = new Date(dDate.setDate(dDate.getDate() + 8)).toLocaleDateString(); // Note: setDate increments relatively
    const day25 = new Date(dDate.setDate(dDate.getDate() + 10)).toLocaleDateString();
    
    const rems = [`Day 7: ${day7}`, `Day 15: ${day15}`, `Day 25: ${day25}`];
    rems.forEach(rem => {
      const chip = document.createElement('span');
      chip.className = 'reminder-chip';
      chip.textContent = rem;
      displayReminderChips.appendChild(chip);
    });
  }

  // Hospital email draft
  if (ev.hospital_email_draft) {
    displayEmailDraftBox.style.display = 'block';
    displayEmailDraft.textContent = ev.hospital_email_draft;
  } else {
    displayEmailDraftBox.style.display = 'none';
  }
  
  // Update PDF download link
  downloadPdfBtn.href = `${API_BASE}/api/claim-form/${claim.claim_case_id}`;
  
  // JSON Output code block
  jsonOutput.textContent = JSON.stringify(claim, null, 2);
  
  // Append real-time logs to terminal body from audit trail
  claim.audit_trail.forEach(log => {
    appendLogLine(log.step, log.action);
  });
}
