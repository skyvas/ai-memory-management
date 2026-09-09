// DataSec DB Frontend Client Application
document.addEventListener('DOMContentLoaded', () => {
  // State
  let authToken = localStorage.getItem('datasec_token') || null;
  let currentUser = { username: 'admin', role: 'admin', display_name: 'Security Administrator' };
  let allFindings = [];
  let selectedFindingId = null;
  let activeFilter = 'ALL';
  let eventSource = null;

  // DOM Elements
  const sseStatusText = document.getElementById('sse-status-text');
  const navUsername = document.getElementById('nav-username');
  const navRole = document.getElementById('nav-role');
  const btnSwitchRole = document.getElementById('btn-switch-role');
  const btnResetSystem = document.getElementById('btn-reset-system');

  // Metrics
  const riskBadge = document.getElementById('risk-badge');
  const riskBarFill = document.getElementById('risk-bar-fill');
  const riskSubtext = document.getElementById('risk-subtext');
  const statVulnCount = document.getElementById('stat-vuln-count');
  const statCritChip = document.getElementById('stat-crit-chip');
  const statHighChip = document.getElementById('stat-high-chip');
  const statMedChip = document.getElementById('stat-med-chip');
  const statFilesCount = document.getElementById('stat-files-count');
  const statRecordsCount = document.getElementById('stat-records-count');

  // Left panel
  const filesListContainer = document.getElementById('ingested-files-list');
  const emptyFilesMsg = document.getElementById('empty-files-msg');
  const filesBadgeCount = document.getElementById('files-badge-count');
  const dropUploadZone = document.getElementById('drop-upload-zone');
  const fileInputHidden = document.getElementById('file-input-hidden');
  const sampleButtons = document.querySelectorAll('.btn-sample');

  // Center panel
  const liveScanBanner = document.getElementById('live-scan-banner');
  const scanStatusMessage = document.getElementById('scan-status-message');
  const scanProgressPct = document.getElementById('scan-progress-pct');
  const scanProgressFill = document.getElementById('scan-progress-fill');
  const findingsContainer = document.getElementById('findings-container');
  const findingsEmptyState = document.getElementById('findings-empty-state');
  const filterTabs = document.querySelectorAll('.tab-btn');
  const tabCountAll = document.getElementById('tab-count-all');
  const tabCountCrit = document.getElementById('tab-count-crit');
  const tabCountHigh = document.getElementById('tab-count-high');
  const tabCountMed = document.getElementById('tab-count-med');

  // Right panel
  const detailEmptyState = document.getElementById('detail-empty-state');
  const activeDetailView = document.getElementById('active-detail-view');
  const detailSeverityBadge = document.getElementById('detail-severity-badge');
  const detailCategoryBadge = document.getElementById('detail-category-badge');
  const detailCweBadge = document.getElementById('detail-cwe-badge');
  const detailTitle = document.getElementById('detail-title');
  const detailFile = document.getElementById('detail-file');
  const detailLine = document.getElementById('detail-line');
  const detailConfidence = document.getElementById('detail-confidence');
  const detailSnippet = document.getElementById('detail-snippet');
  const detailRemediation = document.getElementById('detail-remediation');
  const detailEvidence = document.getElementById('detail-evidence');
  const btnExportReport = document.getElementById('btn-export-report');

  // Modals
  const resetModal = document.getElementById('reset-modal');
  const btnCancelReset = document.getElementById('btn-cancel-reset');
  const btnConfirmReset = document.getElementById('btn-confirm-reset');

  const authModal = document.getElementById('auth-modal');
  const btnCancelAuth = document.getElementById('btn-cancel-auth');
  const btnSubmitLogin = document.getElementById('btn-submit-login');
  const inputUsername = document.getElementById('input-username');
  const inputPassword = document.getElementById('input-password');
  const authErrorMsg = document.getElementById('auth-error-msg');
  const presetAdmin = document.getElementById('preset-admin');
  const presetAnalyst = document.getElementById('preset-analyst');

  const reportModal = document.getElementById('report-modal');
  const btnCloseReport = document.getElementById('btn-close-report');
  const btnCloseReportFooter = document.getElementById('btn-close-report-footer');
  const btnCopyReport = document.getElementById('btn-copy-report');
  const reportMarkdownText = document.getElementById('report-markdown-text');

  // Initialize
  async function init() {
    setupAuthDefaults();
    setupSSE();
    setupEventListeners();
    await fetchInitialState();
  }

  function setupAuthDefaults() {
    if (!authToken) {
      loginUser('admin', 'admin');
    } else {
      verifyToken();
    }
  }

  async function verifyToken() {
    try {
      const res = await fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      const data = await res.json();
      if (data.authenticated) {
        currentUser = data.user;
        updateUserUI();
      } else {
        loginUser('admin', 'admin');
      }
    } catch {
      loginUser('admin', 'admin');
    }
  }

  async function loginUser(username, password) {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      if (!res.ok) {
        throw new Error('Invalid credentials');
      }
      const data = await res.json();
      authToken = data.token;
      currentUser = data.user;
      localStorage.setItem('datasec_token', authToken);
      updateUserUI();
      authModal.style.display = 'none';
    } catch (err) {
      authErrorMsg.textContent = err.message;
      authErrorMsg.style.display = 'block';
    }
  }

  function updateUserUI() {
    navUsername.textContent = currentUser.username;
    navRole.textContent = currentUser.role.toUpperCase();
    if (currentUser.role === 'admin') {
      btnResetSystem.style.display = 'inline-flex';
      dropUploadZone.style.display = 'block';
    } else {
      btnResetSystem.style.display = 'none';
      dropUploadZone.style.display = 'none';
    }
  }

  // SSE Stream
  function setupSSE() {
    if (eventSource) {
      eventSource.close();
    }
    eventSource = new EventSource('/api/stream');

    eventSource.onopen = () => {
      sseStatusText.textContent = 'Live Auditor Active';
    };

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleSSEEvent(payload);
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
      }
    };

    eventSource.onerror = () => {
      sseStatusText.textContent = 'Reconnecting...';
    };
  }

  function handleSSEEvent(payload) {
    if (payload.type === 'status') {
      updateScanProgress(payload.data.text, payload.data.progress);
    } else if (payload.type === 'scan_step') {
      updateScanProgress(payload.data.message, payload.data.progress);
      if (payload.data.finding) {
        addOrUpdateFinding(payload.data.finding);
      }
    } else if (payload.type === 'scan_complete') {
      updateScanProgress('Audit Complete!', 1.0);
      renderScanResults(payload.data.summary, payload.data.state);
    } else if (payload.type === 'system_reset') {
      resetUIState(payload.data.state);
    }
  }

  function updateScanProgress(msg, progress) {
    scanStatusMessage.textContent = msg;
    const pct = Math.round(progress * 100);
    scanProgressPct.textContent = `${pct}%`;
    scanProgressFill.style.width = `${pct}%`;
  }

  async function fetchInitialState() {
    try {
      const res = await fetch('/api/state');
      const state = await res.json();
      if (state.files && state.files.length > 0) {
        renderState(state);
      }
    } catch (err) {
      console.error('Failed to load initial state:', err);
    }
  }

  function renderState(state) {
    allFindings = state.findings || [];
    updateMetrics(state);
    renderFileList(state.files || []);
    renderFindingsList();
    if (allFindings.length > 0) {
      selectFinding(allFindings[0].id);
    }
  }

  function renderScanResults(summary, state) {
    allFindings = summary.findings || [];
    updateMetrics(state);
    renderFileList(state.files || []);
    renderFindingsList();
    if (allFindings.length > 0) {
      selectFinding(allFindings[0].id);
    } else {
      showEmptyDetail();
    }
  }

  function updateMetrics(state) {
    // Risk Score
    const score = state.risk_score || 0;
    riskBadge.textContent = `${score}/100 ${score > 50 ? 'Critical' : score > 20 ? 'Moderate' : 'Clean'}`;
    riskBadge.className = `risk-pill ${score > 50 ? 'critical' : 'clean'}`;
    riskBarFill.className = `risk-bar-fill ${score > 50 ? 'critical' : 'clean'}`;
    riskBarFill.style.width = `${score}%`;

    riskSubtext.textContent = score > 50 
      ? 'Immediate remediation required for production compliance' 
      : score > 0 
      ? 'Low/moderate vulnerabilities detected' 
      : 'Conforms to security and compliance baselines';

    // Vulnerability Counts
    const crit = state.critical_count || 0;
    const high = state.high_count || 0;
    const med = state.medium_count || 0;
    const total = state.total_findings_count || allFindings.length;

    statVulnCount.innerHTML = `${total} <span class="metric-sub-val">Findings</span>`;
    statCritChip.textContent = `${crit} Critical`;
    statHighChip.textContent = `${high} High`;
    statMedChip.textContent = `${med} Med`;

    tabCountAll.textContent = total;
    tabCountCrit.textContent = crit;
    tabCountHigh.textContent = high;
    tabCountMed.textContent = med;

    // Files & Records
    statFilesCount.innerHTML = `${state.files ? state.files.length : 0} <span class="metric-sub-val">Files Ingested</span>`;
    statRecordsCount.innerHTML = `${(state.total_records || 0).toLocaleString()} <span class="metric-sub-val">Records</span>`;
    filesBadgeCount.textContent = state.files ? state.files.length : 0;
  }

  function renderFileList(files) {
    if (!files || files.length === 0) {
      emptyFilesMsg.style.display = 'block';
      filesListContainer.innerHTML = '';
      filesListContainer.appendChild(emptyFilesMsg);
      return;
    }

    emptyFilesMsg.style.display = 'none';
    filesListContainer.innerHTML = '';

    files.forEach(f => {
      const item = document.createElement('div');
      item.className = 'file-item';
      item.innerHTML = `
        <div class="file-item-left">
          <svg class="file-icon" viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" fill="none" stroke-width="2">
            <ellipse cx="12" cy="5" rx="9" ry="3"/>
            <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
          </svg>
          <div>
            <div class="file-meta-name">${f.name}</div>
            <div class="file-meta-sub">${f.type} • ${f.size}</div>
          </div>
        </div>
        <span class="file-action-tag">Audited</span>
      `;
      filesListContainer.appendChild(item);
    });
  }

  function renderFindingsList() {
    findingsContainer.innerHTML = '';
    const filtered = allFindings.filter(f => {
      if (activeFilter === 'ALL') return true;
      return f.severity === activeFilter;
    });

    if (filtered.length === 0) {
      findingsEmptyState.style.display = 'flex';
      findingsContainer.appendChild(findingsEmptyState);
      return;
    }

    findingsEmptyState.style.display = 'none';

    filtered.forEach(f => {
      const card = document.createElement('div');
      const sevClass = f.severity.toLowerCase();
      card.className = `finding-card ${sevClass} ${f.id === selectedFindingId ? 'active' : ''}`;
      card.dataset.id = f.id;

      const complianceBadge = f.compliance_tags && f.compliance_tags.length > 0 
        ? `<span class="category-chip">${f.compliance_tags[0]}</span>` 
        : '';

      card.innerHTML = `
        <div class="finding-card-content">
          <div class="finding-badges">
            <span class="severity-chip ${sevClass}">${f.severity}</span>
            <span class="category-chip">${f.category.replace(/_/g, ' ')}</span>
            ${complianceBadge}
            ${f.cwe_id ? `<span class="category-chip">${f.cwe_id}</span>` : ''}
          </div>
          <div class="finding-title-text">${f.title}</div>
          <div class="finding-sub-meta">${f.file_name} ${f.table_name ? `• Table: ${f.table_name}` : ''} ${f.line_number ? `• Line/Rec: ${f.line_number}` : ''}</div>
        </div>
        <svg viewBox="0 0 24 24" width="16" height="16" stroke="#64748b" fill="none" stroke-width="2">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      `;

      card.addEventListener('click', () => {
        document.querySelectorAll('.finding-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        selectFinding(f.id);
      });

      findingsContainer.appendChild(card);
    });
  }

  function addOrUpdateFinding(finding) {
    if (!allFindings.some(f => f.id === finding.id)) {
      if (allFindings.length < 250) {
        allFindings.push(finding);
      }
      renderFindingsList();
    }
  }

  function selectFinding(findingId) {
    selectedFindingId = findingId;
    const f = allFindings.find(item => item.id === findingId);
    if (!f) {
      showEmptyDetail();
      return;
    }

    detailEmptyState.style.display = 'none';
    activeDetailView.style.display = 'block';

    const sevClass = f.severity.toLowerCase();
    detailSeverityBadge.className = `severity-badge ${sevClass}`;
    detailSeverityBadge.textContent = f.severity;
    detailCategoryBadge.textContent = f.category;

    const complianceList = (f.compliance_tags && f.compliance_tags.length > 0)
      ? ` • ${f.compliance_tags.join(', ')}`
      : '';
    detailCweBadge.textContent = `${f.cwe_id || 'CWE-VULN'}${complianceList}`;

    detailTitle.textContent = f.title;
    detailFile.textContent = f.file_name;
    detailLine.textContent = f.line_number || (f.table_name ? `Table ${f.table_name}` : 'N/A');
    detailConfidence.textContent = `${Math.round((f.confidence || 0.95) * 100)}%`;

    detailSnippet.innerHTML = `<code>${escapeHtml(f.snippet)}</code>`;
    detailRemediation.textContent = f.remediation;
    detailEvidence.textContent = f.evidence;
  }

  function showEmptyDetail() {
    detailEmptyState.style.display = 'flex';
    activeDetailView.style.display = 'none';
  }

  function resetUIState(state) {
    allFindings = [];
    selectedFindingId = null;
    updateMetrics(state || {});
    renderFileList([]);
    renderFindingsList();
    showEmptyDetail();
    updateScanProgress('System reset complete. Ready for new ingestion.', 0);
  }

  // Scanning Trigger
  async function triggerScan(sampleId = null, filePath = null) {
    updateScanProgress(`Preparing to audit ${sampleId || filePath}...`, 0.05);

    try {
      const res = await fetch('/api/scan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ sample_id: sampleId, file_path: filePath })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Scan failed');
      }

      const summary = await res.json();
    } catch (err) {
      updateScanProgress(`Scan error: ${err.message}`, 0);
    }
  }

  // File Upload Handlers
  async function handleFileUpload(file) {
    if (currentUser.role !== 'admin') {
      alert('Only users with Admin role can upload database files.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    updateScanProgress(`Uploading ${file.name}...`, 0.1);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authToken}` },
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const uploadData = await res.json();
      await triggerScan(null, uploadData.file_path);
    } catch (err) {
      updateScanProgress(`Upload failed: ${err.message}`, 0);
    }
  }

  function setupEventListeners() {
    // Sample Audits
    sampleButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const sampleId = btn.dataset.sample;
        triggerScan(sampleId);
      });
    });

    // Filter Tabs
    filterTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        filterTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        activeFilter = tab.dataset.filter;
        renderFindingsList();
      });
    });

    // Drag and Drop Upload
    dropUploadZone.addEventListener('click', () => fileInputHidden.click());
    fileInputHidden.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        handleFileUpload(e.target.files[0]);
      }
    });

    dropUploadZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropUploadZone.classList.add('dragover');
    });

    dropUploadZone.addEventListener('dragleave', () => {
      dropUploadZone.classList.remove('dragover');
    });

    dropUploadZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropUploadZone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFileUpload(e.dataTransfer.files[0]);
      }
    });

    // Reset System Modal
    btnResetSystem.addEventListener('click', () => {
      if (currentUser.role !== 'admin') {
        alert('Permission denied: Only Admin users have privileges to reset system data.');
        return;
      }
      resetModal.style.display = 'flex';
    });

    btnCancelReset.addEventListener('click', () => {
      resetModal.style.display = 'none';
    });

    btnConfirmReset.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/reset', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Reset failed');
        }
        resetModal.style.display = 'none';
      } catch (err) {
        alert(`Reset error: ${err.message}`);
      }
    });

    // Switch Role / Auth Modal
    btnSwitchRole.addEventListener('click', () => {
      authErrorMsg.style.display = 'none';
      authModal.style.display = 'flex';
    });

    btnCancelAuth.addEventListener('click', () => {
      authModal.style.display = 'none';
    });

    presetAdmin.addEventListener('click', () => {
      inputUsername.value = 'admin';
      inputPassword.value = 'admin';
    });

    presetAnalyst.addEventListener('click', () => {
      inputUsername.value = 'analyst';
      inputPassword.value = 'analyst';
    });

    btnSubmitLogin.addEventListener('click', (e) => {
      e.preventDefault();
      loginUser(inputUsername.value, inputPassword.value);
    });

    // Export Report
    btnExportReport.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/report/markdown');
        if (!res.ok) {
          alert('Please run an audit before exporting a report.');
          return;
        }
        const data = await res.json();
        reportMarkdownText.textContent = data.markdown;
        reportModal.style.display = 'flex';
      } catch (err) {
        alert('Failed to generate export report.');
      }
    });

    const closeReport = () => { reportModal.style.display = 'none'; };
    btnCloseReport.addEventListener('click', closeReport);
    btnCloseReportFooter.addEventListener('click', closeReport);

    btnCopyReport.addEventListener('click', () => {
      navigator.clipboard.writeText(reportMarkdownText.textContent);
      btnCopyReport.textContent = 'Copied!';
      setTimeout(() => { btnCopyReport.textContent = 'Copy Markdown'; }, 2000);
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  init();
});
