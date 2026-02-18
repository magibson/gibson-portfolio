// Jarvis Prospector — Popup Script
// Polls chrome.storage.local directly for progress (survives page reloads)

const $ = (sel) => document.querySelector(sel);
const STORAGE_KEY = 'jarvisScrapeState';

let collectedLeads = [];
let campaigns = [];
let selectedCampaign = null;
let settings = { apiUrl: 'http://100.83.250.65:8089', maxPages: 0, searchName: '' };

// Load saved settings
chrome.storage.local.get(['jarvisSettings', 'jarvisSelectedCampaignId'], (result) => {
  if (result.jarvisSettings) {
    settings = { ...settings, ...result.jarvisSettings };
    $('#apiUrl').value = settings.apiUrl;
    $('#maxPages').value = settings.maxPages;
    $('#searchName').value = settings.searchName || '';
  }
  checkServerConnection();
  loadCampaigns(result.jarvisSelectedCampaignId || null);
});

$('#btnSaveSettings').addEventListener('click', () => {
  settings.apiUrl = $('#apiUrl').value.replace(/\/$/, '');
  settings.maxPages = parseInt($('#maxPages').value) || 0;
  settings.searchName = $('#searchName').value;
  chrome.storage.local.set({ jarvisSettings: settings });
  checkServerConnection();
  loadCampaigns();
});

$('#campaignSelect').addEventListener('change', () => {
  const val = $('#campaignSelect').value;
  selectedCampaign = val ? campaigns.find(c => c.id === parseInt(val)) : null;
  chrome.storage.local.set({ jarvisSelectedCampaignId: val ? parseInt(val) : null });
  updateCampaignUI();
});

$('#btnOpenSearch').addEventListener('click', () => {
  if (selectedCampaign && selectedCampaign.sales_nav_url) {
    chrome.tabs.create({ url: selectedCampaign.sales_nav_url });
  }
});

async function loadCampaigns(restoreId) {
  try {
    const resp = await fetch(settings.apiUrl + '/api/campaigns', { signal: AbortSignal.timeout(5000) });
    if (!resp.ok) return;
    const data = await resp.json();
    campaigns = (data.campaigns || []).filter(c => c.status === 'active');
    const sel = $('#campaignSelect');
    sel.innerHTML = '<option value="">— No Campaign —</option>';
    campaigns.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = `${c.name} (${c.leads_count} leads)`;
      sel.appendChild(opt);
    });
    if (restoreId) {
      sel.value = restoreId;
      selectedCampaign = campaigns.find(c => c.id === parseInt(restoreId)) || null;
    }
    updateCampaignUI();
  } catch { }
}

function updateCampaignUI() {
  const btn = $('#btnOpenSearch');
  btn.style.display = (selectedCampaign && selectedCampaign.sales_nav_url && selectedCampaign.sales_nav_url.trim()) ? '' : 'none';
  if (selectedCampaign) {
    $('#searchName').value = selectedCampaign.name;
    settings.searchName = selectedCampaign.name;
  }
}

async function checkServerConnection() {
  try {
    const resp = await fetch(settings.apiUrl + '/api/dashboard', { signal: AbortSignal.timeout(5000) });
    if (resp.ok) {
      $('#serverStatus').className = 'status connected';
      $('#serverStatus').textContent = '● Connected';
    } else throw new Error();
  } catch {
    $('#serverStatus').className = 'status disconnected';
    $('#serverStatus').textContent = '● Disconnected';
  }
}

// Poll storage directly — works even when content script is on a different page mid-navigation
function checkStatus() {
  chrome.storage.local.get([STORAGE_KEY], (result) => {
    const state = result[STORAGE_KEY] || null;

    // Also check if we're on a search page via tab URL
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0];
      const isOnSalesNav = tab && tab.url && tab.url.includes('/sales/');

      if (!isOnSalesNav && !state) {
        $('#pageStatus').textContent = 'Navigate to Sales Navigator search results to begin.';
        $('#pageStatus').className = 'page-status error';
        $('#btnScrape').disabled = true;
        $('#btnScrape').style.display = '';
        $('#btnStop').style.display = 'none';
        $('#progress').style.display = 'none';
        return;
      }

      // In-progress scrape
      if (state && state.inProgress) {
        const leadsCount = (state.leads || []).length;
        const page = state.currentPage || 1;
        const total = state.totalPages || '?';
        $('#pageStatus').textContent = `Scraping page ${page} of ${total}... (${leadsCount} leads so far)`;
        $('#pageStatus').className = 'page-status ready';
        $('#btnScrape').style.display = 'none';
        $('#btnStop').style.display = '';
        $('#progress').style.display = '';
        const pct = total > 0 ? Math.round(((page - 1) / total) * 100) : 0;
        $('#progressFill').style.width = pct + '%';
        $('#progressText').textContent = `Page ${page} of ${total}... (${leadsCount} leads)`;
        return;
      }

      // Completed scrape
      if (state && state.completed && state.leads && state.leads.length > 0) {
        collectedLeads = state.leads;
        if (state.searchName) collectedLeads.forEach(l => l.search_name = state.searchName);
        $('#pageStatus').textContent = `Scrape complete! ${state.totalLeads || state.leads.length} leads ready.`;
        $('#pageStatus').className = 'page-status ready';
        $('#btnScrape').style.display = '';
        $('#btnScrape').disabled = false;
        $('#btnScrape').textContent = 'Scrape Again';
        $('#btnStop').style.display = 'none';
        $('#progress').style.display = 'none';
        $('#stats').style.display = 'flex';
        $('#statLeads').textContent = state.totalLeads || state.leads.length;
        $('#btnSend').disabled = false;
        return;
      }

      // Ready state — try sending message to content script to verify it's loaded
      if (isOnSalesNav) {
        chrome.tabs.sendMessage(tab.id, { type: 'GET_STATUS' }, (resp) => {
          if (chrome.runtime.lastError || !resp) {
            $('#pageStatus').textContent = 'Content script not loaded. Refresh the Sales Nav page.';
            $('#pageStatus').className = 'page-status error';
            $('#btnScrape').disabled = true;
            return;
          }
          if (!resp.isSearchPage) {
            $('#pageStatus').textContent = 'This is not a search results page.';
            $('#pageStatus').className = 'page-status error';
            $('#btnScrape').disabled = true;
            return;
          }
          $('#pageStatus').textContent = 'Ready to scrape this search.';
          $('#pageStatus').className = 'page-status ready';
          $('#btnScrape').style.display = '';
          $('#btnScrape').disabled = false;
          $('#btnScrape').textContent = 'Start Scraping';
          $('#btnStop').style.display = 'none';
          $('#progress').style.display = 'none';
        });
      }
    });
  });
}

checkStatus();
setInterval(checkStatus, 1500);

// Start scraping
$('#btnScrape').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  collectedLeads = [];
  $('#btnScrape').style.display = 'none';
  $('#btnStop').style.display = '';
  $('#progress').style.display = '';
  $('#stats').style.display = 'none';
  $('#sendResult').style.display = 'none';
  $('#btnSend').disabled = true;
  $('#progressText').textContent = 'Starting scrape...';
  $('#progressFill').style.width = '0%';

  const searchName = selectedCampaign ? selectedCampaign.name : settings.searchName;

  // Clear old state first, then start
  chrome.storage.local.remove(STORAGE_KEY, () => {
    chrome.tabs.sendMessage(tab.id, {
      type: 'START_SCRAPE',
      maxPages: settings.maxPages,
      searchName: searchName
    }, (resp) => {
      if (chrome.runtime.lastError) {
        $('#pageStatus').textContent = 'Failed to start. Refresh the page and try again.';
        $('#pageStatus').className = 'page-status error';
        $('#btnScrape').style.display = '';
        $('#btnStop').style.display = 'none';
        $('#progress').style.display = 'none';
      }
    });
  });
});

// Stop scraping
$('#btnStop').addEventListener('click', async () => {
  // Set shouldStop directly in storage (works even if content script is mid-navigation)
  chrome.storage.local.get([STORAGE_KEY], (result) => {
    const state = result[STORAGE_KEY];
    if (state && state.inProgress) {
      chrome.storage.local.set({ [STORAGE_KEY]: { ...state, shouldStop: true } });
    }
  });
});

// Send leads to server
$('#btnSend').addEventListener('click', async () => {
  if (collectedLeads.length === 0) return;

  $('#btnSend').disabled = true;
  $('#btnSend').textContent = 'Sending...';
  $('#sendResult').style.display = 'none';

  const searchName = selectedCampaign ? selectedCampaign.name : settings.searchName;
  const payload = { leads: collectedLeads, search_name: searchName };
  if (selectedCampaign) payload.campaign_id = selectedCampaign.id;

  try {
    const resp = await fetch(settings.apiUrl + '/api/leads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if (resp.ok) {
      $('#statNew').textContent = data.new || 0;
      $('#statDupes').textContent = data.duplicates || 0;
      $('#sendResult').textContent = `✓ Sent! ${data.new || 0} new leads added, ${data.duplicates || 0} duplicates skipped.`;
      $('#sendResult').className = 'send-result success';
      chrome.storage.local.remove(STORAGE_KEY);
      loadCampaigns(selectedCampaign ? selectedCampaign.id : null);
    } else {
      throw new Error(data.error || 'Server error');
    }
  } catch (err) {
    $('#sendResult').textContent = `✗ Failed: ${err.message}`;
    $('#sendResult').className = 'send-result error';
  }

  $('#sendResult').style.display = '';
  $('#btnSend').disabled = false;
  $('#btnSend').textContent = 'Send to Jarvis';
});

setInterval(checkServerConnection, 30000);
