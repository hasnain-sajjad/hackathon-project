// NovaWorks AI Project Management CRM Frontend Logic
(function() {
  const API_BASE = '/api';

  // Application State
  const state = {
    user: null,
    currentView: 'projects',
    currentProjectId: null,
    projects: [],
    projectDetail: null,
    myTasks: [],
    users: [],
    isLoading: false
  };

  // DOM Elements
  const el = {
    loginView: document.getElementById('login-view'),
    appView: document.getElementById('app-view'),
    loginForm: document.getElementById('login-form'),
    loginEmail: document.getElementById('login-email'),
    loginPassword: document.getElementById('login-password'),
    loginError: document.getElementById('login-error'),
    userAvatar: document.getElementById('user-avatar'),
    userName: document.getElementById('user-name'),
    userRoleBadge: document.getElementById('user-role-badge'),
    userSpec: document.getElementById('user-spec'),
    pageTitle: document.getElementById('page-title'),
    pageSubtitle: document.getElementById('page-subtitle'),
    topbarActions: document.getElementById('topbar-actions'),
    contentArea: document.getElementById('content-area'),
    modalBackdrop: document.getElementById('transcript-modal'),
    transcriptInput: document.getElementById('transcript-input'),
    btnProcessTranscript: document.getElementById('btn-process-transcript'),
    transcriptError: document.getElementById('transcript-error'),
    toastContainer: document.getElementById('toast-container'),
    accountSwitcher: document.getElementById('account-switcher-select')
  };

  // Toast Notification Helper
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    el.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // API Client
  async function apiFetch(endpoint, options = {}) {
    options.headers = options.headers || {};
    options.headers['Content-Type'] = 'application/json';
    try {
      const resp = await fetch(`${API_BASE}${endpoint}`, options);
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error || (data.details ? data.details.join(', ') : 'API request failed'));
      }
      return data;
    } catch (err) {
      throw err;
    }
  }

  // Auth Handling
  async function checkAuth() {
    try {
      const res = await apiFetch('/auth/me');
      if (res && res.user) {
        state.user = res.user;
        renderApp();
      } else {
        renderLogin();
      }
    } catch {
      renderLogin();
    }
  }

  async function login(email, password) {
    try {
      el.loginError.style.display = 'none';
      const res = await apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      state.user = res.user;
      showToast(`Welcome back, ${state.user.name}!`, 'success');
      renderApp();
    } catch (err) {
      el.loginError.textContent = err.message;
      el.loginError.style.display = 'block';
    }
  }

  async function logout() {
    try {
      await apiFetch('/auth/logout', { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
    state.user = null;
    showToast('Logged out successfully', 'info');
    renderLogin();
  }

  // Switch demo account instantly (Judge tool)
  window.switchDemoUser = async function(email) {
    await login(email, 'Demo123!');
  };

  // Rendering Functions
  function renderLogin() {
    el.loginView.style.display = 'flex';
    el.appView.style.display = 'none';
    el.loginEmail.value = 'admin@novaworks.example';
    el.loginPassword.value = 'Demo123!';
  }

  function renderApp() {
    el.loginView.style.display = 'none';
    el.appView.style.display = 'flex';

    // Sidebar user profile
    el.userName.textContent = state.user.name;
    el.userAvatar.textContent = state.user.name.charAt(0);
    el.userSpec.textContent = state.user.specialization || state.user.role;
    
    // Role Badge
    el.userRoleBadge.className = `badge badge-${state.user.role.toLowerCase()}`;
    el.userRoleBadge.textContent = state.user.role;

    // Account switcher dropdown
    if (el.accountSwitcher) {
      el.accountSwitcher.value = state.user.email;
    }

    // Role-specific Nav Items
    const btnTranscriptNav = document.getElementById('nav-create-transcript');
    if (btnTranscriptNav) {
      btnTranscriptNav.style.display = state.user.role === 'ADMIN' ? 'flex' : 'none';
    }

    // Default route
    navigateTo('projects');
  }

  // Navigation
  window.navigateTo = function(view, projectId = null) {
    state.currentView = view;
    state.currentProjectId = projectId;

    // Update active nav links
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.remove('active');
      if (item.getAttribute('data-view') === view) {
        item.classList.add('active');
      }
    });

    if (view === 'projects') {
      loadProjectsView();
    } else if (view === 'project-detail') {
      loadProjectDetailView(projectId);
    } else if (view === 'my-tasks') {
      loadMyTasksView();
    } else if (view === 'team') {
      loadTeamDirectoryView();
    }
  };

  // View: Projects List
  async function loadProjectsView() {
    el.pageTitle.textContent = state.user.role === 'ADMIN' 
      ? 'All Client Projects' 
      : (state.user.role === 'MANAGER' ? 'My Managed Projects' : 'My Assigned Projects');
    
    el.pageSubtitle.textContent = state.user.role === 'ADMIN'
      ? 'Global oversight of all client initiatives and delivery roadmaps.'
      : (state.user.role === 'MANAGER' 
          ? `Projects managed by ${state.user.name} (filtered by manager access).` 
          : `Projects where you have assigned development tasks.`);

    // Topbar actions
    if (state.user.role === 'ADMIN') {
      el.topbarActions.innerHTML = `
        <button class="btn btn-secondary btn-sm" onclick="resetDemoData()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>
          Reset Demo
        </button>
        <button class="btn btn-primary btn-sm" onclick="openTranscriptModal()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          Create from Transcript
        </button>
      `;
    } else {
      el.topbarActions.innerHTML = '';
    }

    el.contentArea.innerHTML = `<div style="text-align:center; padding: 40px;"><div class="spinner" style="border-top-color:var(--primary); margin: 0 auto 12px;"></div>Loading projects...</div>`;

    try {
      const res = await apiFetch('/projects');
      state.projects = res.projects || [];
      renderProjectsGrid();
    } catch (err) {
      el.contentArea.innerHTML = `<div class="error-box">Error loading projects: ${err.message}</div>`;
    }
  }

  function renderProjectsGrid() {
    if (state.projects.length === 0) {
      el.contentArea.innerHTML = `
        <div style="text-align: center; padding: 60px 20px; background: #fff; border: 1px dashed var(--border); border-radius: var(--radius-md);">
          <div style="font-size: 2.5rem; margin-bottom: 12px;">📁</div>
          <h3 style="font-size: 1.2rem; font-weight: 700; margin-bottom: 8px;">No Projects Found</h3>
          <p style="color: var(--text-muted); max-width: 440px; margin: 0 auto 20px; font-size: 0.9rem;">
            ${state.user.role === 'ADMIN' 
              ? 'No projects have been created yet. Paste a meeting transcript to automatically extract projects and tasks.'
              : 'You have no assigned projects in this workspace.'}
          </p>
          ${state.user.role === 'ADMIN' ? `<button class="btn btn-primary" onclick="openTranscriptModal()">Create from Transcript</button>` : ''}
        </div>
      `;
      return;
    }

    let html = `
      <div class="info-banner">
        <div class="info-banner-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
        </div>
        <div class="info-banner-content">
          <h4>Role-Based Access: ${state.user.role}</h4>
          <p>${state.user.role === 'ADMIN' 
            ? 'You have administrative access to view all projects and convert transcripts into deliverables.' 
            : (state.user.role === 'MANAGER' 
                ? 'Manager isolation active: you only see projects assigned to you and all their tasks.' 
                : 'Agent isolation active: you only see projects where you have assigned tasks, and other agents\' tasks are strictly hidden.')}
          </p>
        </div>
      </div>
      <div class="grid-cards">
    `;

    state.projects.forEach(p => {
      html += `
        <div class="project-card">
          <div class="project-card-header">
            <div class="project-card-title">
              <h3>${escapeHtml(p.name)}</h3>
              <p>Client: <strong>${escapeHtml(p.clientName)}</strong></p>
            </div>
            <span class="badge badge-info">${p.id}</span>
          </div>
          <p class="project-card-desc">${escapeHtml(p.description || 'No description provided.')}</p>
          <div class="project-card-meta">
            <div class="project-card-stat">
              <span class="stat-item" title="Tasks">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                ${p.taskCount} tasks
              </span>
              <span class="stat-item" title="Estimated Hours">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                ${p.totalHours}h
              </span>
            </div>
            <div>
              <span>Deadline: <strong>${p.deadline}</strong></span>
            </div>
          </div>
          <div style="margin-top: 16px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.8rem; color: var(--text-muted);">Manager: <strong>${escapeHtml(p.managerName)}</strong></span>
            <button class="btn btn-secondary btn-sm" onclick="navigateTo('project-detail', '${p.id}')">View Details &rarr;</button>
          </div>
        </div>
      `;
    });

    html += `</div>`;
    el.contentArea.innerHTML = html;
  }

  // View: Project Detail
  async function loadProjectDetailView(projectId) {
    el.topbarActions.innerHTML = `
      <button class="btn btn-secondary btn-sm" onclick="navigateTo('projects')">&larr; Back to Projects</button>
    `;
    el.contentArea.innerHTML = `<div style="text-align:center; padding: 40px;"><div class="spinner" style="border-top-color:var(--primary); margin: 0 auto 12px;"></div>Loading project details...</div>`;

    try {
      const res = await apiFetch(`/projects/${projectId}`);
      const p = res.project;
      state.projectDetail = p;

      el.pageTitle.textContent = p.name;
      el.pageSubtitle.textContent = `Client: ${p.clientName} | Delivery Target: ${p.deadline}`;

      let tasksHtml = '';
      if (!p.tasks || p.tasks.length === 0) {
        tasksHtml = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 32px;">No tasks available for your access role.</td></tr>`;
      } else {
        p.tasks.forEach(t => {
          tasksHtml += `
            <tr>
              <td>
                <div style="font-weight: 600; color: var(--text-main);">${escapeHtml(t.title)}</div>
                <div style="font-size: 0.8rem; color: var(--text-muted); max-width: 420px;">${escapeHtml(t.description || '')}</div>
              </td>
              <td>
                <span style="font-weight: 500;">${escapeHtml(t.assigneeName)}</span>
                <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(t.assigneeSpecialization || '')}</div>
              </td>
              <td>
                <span class="badge badge-info">${t.deadline}</span>
              </td>
              <td>
                <strong>${t.estimatedHours} hrs</strong>
              </td>
              <td>
                <span class="badge ${t.assigneeId === state.user.id ? 'badge-agent' : 'badge-info'}">
                  ${t.assigneeId === state.user.id ? 'Assigned to You' : 'Planned'}
                </span>
              </td>
            </tr>
          `;
        });
      }

      el.contentArea.innerHTML = `
        <div class="detail-header">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
              <span class="badge badge-info" style="margin-bottom: 8px;">${p.id}</span>
              <h3 style="font-size: 1.4rem; font-weight: 700; margin-bottom: 6px;">${escapeHtml(p.name)}</h3>
              <p style="color: var(--text-muted); font-size: 0.95rem;">${escapeHtml(p.description || '')}</p>
            </div>
            <div style="text-align: right;">
              <span class="badge badge-manager">Managed by ${escapeHtml(p.managerName)}</span>
            </div>
          </div>
          <div class="detail-meta-grid">
            <div class="meta-box">
              <h5>Client Name</h5>
              <p>${escapeHtml(p.clientName)}</p>
            </div>
            <div class="meta-box">
              <h5>Project Deadline</h5>
              <p>${p.deadline}</p>
            </div>
            <div class="meta-box">
              <h5>Visible Tasks</h5>
              <p>${p.tasks ? p.tasks.length : 0} tasks</p>
            </div>
            <div class="meta-box">
              <h5>Total Estimated Hours</h5>
              <p>${p.tasks ? p.tasks.reduce((sum, t) => sum + t.estimatedHours, 0) : 0} hrs</p>
            </div>
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h4 style="font-size: 1.1rem; font-weight: 700;">
            ${state.user.role === 'AGENT' ? 'Your Assigned Tasks for this Project' : 'Project Task Breakdown'}
          </h4>
          <span style="font-size: 0.82rem; color: var(--text-muted);">
            ${state.user.role === 'AGENT' ? 'Strict Isolation: Only your assigned tasks are shown' : 'All approved project deliverables'}
          </span>
        </div>

        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 35%;">Task Details</th>
                <th style="width: 25%;">Assigned Agent</th>
                <th style="width: 15%;">Deadline</th>
                <th style="width: 12%;">Effort</th>
                <th style="width: 13%;">Status</th>
              </tr>
            </thead>
            <tbody>
              ${tasksHtml}
            </tbody>
          </table>
        </div>
      `;
    } catch (err) {
      el.contentArea.innerHTML = `
        <div class="error-box">
          <h4>Access Denied or Not Found</h4>
          <p>${err.message}</p>
          <button class="btn btn-secondary btn-sm" style="margin-top: 12px;" onclick="navigateTo('projects')">&larr; Return to Permitted Projects</button>
        </div>
      `;
    }
  }

  // View: My Tasks Screen
  async function loadMyTasksView() {
    el.pageTitle.textContent = state.user.role === 'AGENT' 
      ? 'My Assigned Tasks' 
      : (state.user.role === 'MANAGER' ? 'Managed Project Tasks' : 'All Project Tasks');
    
    el.pageSubtitle.textContent = state.user.role === 'AGENT'
      ? `Filtered exclusively to development work assigned to ${state.user.name}.`
      : 'Comprehensive work item view across projects.';

    el.topbarActions.innerHTML = '';
    el.contentArea.innerHTML = `<div style="text-align:center; padding: 40px;"><div class="spinner" style="border-top-color:var(--primary); margin: 0 auto 12px;"></div>Loading tasks...</div>`;

    try {
      const res = await apiFetch('/tasks');
      state.myTasks = res.tasks || [];
      renderMyTasksTable();
    } catch (err) {
      el.contentArea.innerHTML = `<div class="error-box">Error loading tasks: ${err.message}</div>`;
    }
  }

  function renderMyTasksTable() {
    if (state.myTasks.length === 0) {
      el.contentArea.innerHTML = `
        <div style="text-align: center; padding: 60px 20px; background: #fff; border: 1px dashed var(--border); border-radius: var(--radius-md);">
          <div style="font-size: 2.5rem; margin-bottom: 12px;">📝</div>
          <h3 style="font-size: 1.2rem; font-weight: 700; margin-bottom: 8px;">No Tasks Assigned</h3>
          <p style="color: var(--text-muted); font-size: 0.9rem;">There are no tasks assigned to your account at this moment.</p>
        </div>
      `;
      return;
    }

    let rowsHtml = '';
    state.myTasks.forEach(t => {
      rowsHtml += `
        <tr>
          <td>
            <div style="font-weight: 600; color: var(--text-main);">${escapeHtml(t.title)}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(t.description || '')}</div>
          </td>
          <td>
            <div style="font-weight: 600;">${escapeHtml(t.projectName)}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">Client: ${escapeHtml(t.clientName)}</div>
          </td>
          <td>
            <div style="font-weight: 500;">${escapeHtml(t.assigneeName)}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(t.assigneeSpecialization || '')}</div>
          </td>
          <td>
            <span class="badge badge-info">${t.deadline}</span>
          </td>
          <td>
            <strong>${t.estimatedHours} hrs</strong>
          </td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="navigateTo('project-detail', '${t.projectId}')">Project &rarr;</button>
          </td>
        </tr>
      `;
    });

    el.contentArea.innerHTML = `
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 30%;">Task</th>
              <th style="width: 22%;">Project / Client</th>
              <th style="width: 20%;">Assignee</th>
              <th style="width: 12%;">Deadline</th>
              <th style="width: 8%;">Effort</th>
              <th style="width: 8%;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;
  }

  // View: Read-only Team Directory
  async function loadTeamDirectoryView() {
    el.pageTitle.textContent = 'NovaWorks Team Directory';
    el.pageSubtitle.textContent = 'Read-only organization directory of administrator, project managers, and developer agents.';
    el.topbarActions.innerHTML = '';
    el.contentArea.innerHTML = `<div style="text-align:center; padding: 40px;"><div class="spinner" style="border-top-color:var(--primary); margin: 0 auto 12px;"></div>Loading team directory...</div>`;

    try {
      const res = await apiFetch('/users');
      state.users = res.users || [];
      renderTeamDirectory();
    } catch (err) {
      el.contentArea.innerHTML = `<div class="error-box">Error loading directory: ${err.message}</div>`;
    }
  }

  function renderTeamDirectory() {
    let rowsHtml = '';
    state.users.forEach(u => {
      const skillsHtml = (u.skills || []).map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('');
      rowsHtml += `
        <tr>
          <td>
            <span class="badge badge-info">${u.id}</span>
          </td>
          <td>
            <div style="font-weight: 600; color: var(--text-main);">${escapeHtml(u.name)}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(u.email)}</div>
          </td>
          <td>
            <span class="badge badge-${u.role.toLowerCase()}">${u.role}</span>
          </td>
          <td>
            ${escapeHtml(u.specialization || '')}
          </td>
          <td>
            ${skillsHtml}
          </td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="switchDemoUser('${u.email}')">Log in as</button>
          </td>
        </tr>
      `;
    });

    el.contentArea.innerHTML = `
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 8%;">Ref</th>
              <th style="width: 24%;">Team Member</th>
              <th style="width: 12%;">Role</th>
              <th style="width: 22%;">Specialization</th>
              <th style="width: 24%;">Skills</th>
              <th style="width: 10%;">Quick Switch</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;
  }

  // Transcript Automation Modal Controls
  window.openTranscriptModal = function() {
    el.transcriptError.style.display = 'none';
    if (!el.transcriptInput.value.trim() && window.NovaWorksTranscripts) {
      el.transcriptInput.value = window.NovaWorksTranscripts.supplied;
    }
    el.modalBackdrop.classList.add('active');
  };

  window.closeTranscriptModal = function() {
    el.modalBackdrop.classList.remove('active');
  };

  window.loadSuppliedTranscript = function() {
    if (window.NovaWorksTranscripts) {
      el.transcriptInput.value = window.NovaWorksTranscripts.supplied;
      showToast('Loaded standard 60-minute planning meeting transcript', 'info');
    }
  };

  window.loadModifiedTranscript = function() {
    if (window.NovaWorksTranscripts) {
      el.transcriptInput.value = window.NovaWorksTranscripts.modified;
      showToast('Loaded modified transcript (QuickServe 12h, 23 Oct) for AI test', 'info');
    }
  };

  window.processTranscript = async function() {
    const text = el.transcriptInput.value.trim();
    if (!text) {
      el.transcriptError.innerHTML = '<strong>Error:</strong> Transcript cannot be empty.';
      el.transcriptError.style.display = 'block';
      return;
    }

    // Disable repeated clicks
    el.btnProcessTranscript.disabled = true;
    el.btnProcessTranscript.innerHTML = `<div class="spinner"></div> AI Processing...`;
    el.transcriptError.style.display = 'none';

    try {
      const res = await apiFetch('/transcript/create', {
        method: 'POST',
        body: JSON.stringify({ transcript: text })
      });

      showToast(`Success: Created ${res.projectsCreated} projects and ${res.tasksCreated} tasks!`, 'success');
      closeTranscriptModal();
      navigateTo('projects');
    } catch (err) {
      let errMsg = `<strong>Failed to process transcript:</strong> ${escapeHtml(err.message)}`;
      el.transcriptError.innerHTML = errMsg;
      el.transcriptError.style.display = 'block';
    } finally {
      el.btnProcessTranscript.disabled = false;
      el.btnProcessTranscript.innerHTML = `Process & Generate Projects`;
    }
  };

  // Reset Demo Project Data (Admin only)
  window.resetDemoData = async function() {
    if (!confirm('Are you sure you want to clear all projects and tasks for a fresh demonstration?')) {
      return;
    }
    try {
      await apiFetch('/reset-data', { method: 'POST' });
      showToast('All projects and tasks cleared successfully', 'info');
      navigateTo('projects');
    } catch (err) {
      showToast(`Reset failed: ${err.message}`, 'error');
    }
  };

  // Helper escape HTML
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Event Listeners
  el.loginForm.addEventListener('submit', (e) => {
    e.preventDefault();
    login(el.loginEmail.value, el.loginPassword.value);
  });

  document.getElementById('btn-logout').addEventListener('click', logout);

  // Initialize
  checkAuth();
})();
