// Jarvis Prospector — Popup Script
// Uses chrome.storage.local for state persistence across page reloads

const $ = (sel) => document.querySelector(sel);

let collectedLeads = [];
let settings = {
  apiUrl: 'http://100.83.250.65:8089',
  maxPages: 0,
  searchName: ''
};

// Load saved settings
chrome.storage.local.get(['jarvisSettings'], (result) => {
  if (result.jarvisSettings) {
    settings = { ...settings, ...result.jarvisSettings };
    $('#apiUrl').value = settings.apiUrl;
    $('#maxPages').value = settings.maxPages;
    $('#searchName').value = settings.searchName || '';
  }
  checkServerConnection();
});

// Save settings
$('#btnSaveSettings').addEventListener('click', () => {
  settings.apiUrl = $('#apiUrl').value.replace(/\/$/, '');
  settings.maxPages = parseInt($('#maxPages').value) || 0;
  settings.searchName = $('#searchName').value;
  chrome.storage.local.set({ jarvisSettings: settings });
  checkServerConnection();
});

// Check if server is reachable
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

// Check current tab status — polls storage-based state
async function checkPageStatus() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url || !tab.url.includes('/sales/')) {
      $('#pageStatus').textContent = 'Navigate to Sales Navigator search results to begin.';
      $('#pageStatus').className = 'page-status error';
      $('#btnScrape').disabled = true;
      return;
    }

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

      if (resp.isScraping) {
        // Scrape in progress (multi-page, navigating between pages)
        $('#pageStatus').textContent = `Scraping in progress... page ${resp.currentPage} of ${resp.totalPages} (${resp.leadsFound} leads so far)`;
        $('#pageStatus').className = 'page-status ready';
        $('#btnScrape').style.display = 'none';
        $('#btnStop').style.display = '';
        $('#progress').style.display = '';
        const pct = Math.round(((resp.currentPage - 1) / resp.totalPages) * 100);
        $('#progressFill').style.width = pct + '%';
        $('#progressText').textContent = `Page ${resp.currentPage} of ${resp.totalPages}... (${resp.leadsFound} leads)`;
        return;
      }

      if (resp.completed && resp.leads && resp.leads.length > 0) {
        // Scrape completed — show results
        collectedLeads = resp.leads;
        if (resp.searchName) {
          collectedLeads.forEach(l => l.search_name = resp.searchName);
        }
        $('#pageStatus').textContent = `Scrape complete! ${resp.totalLeads} leads ready.`;
        $('#pageStatus').className = 'page-status ready';
        $('#btnScrape').style.display = '';
        $('#btnScrape').disabled = false;
        $('#btnScrape').textContent = 'Scrape Again';
        $('#btnStop').style.display = 'none';
        $('#progress').style.display = 'none';
        $('#stats').style.display = 'flex';
        $('#statLeads').textContent = resp.totalLeads;
        $('#btnSend').disabled = false;
        return;
      }

      // Ready to scrape
      $('#pageStatus').textContent = 'Ready to scrape this search.';
      $('#pageStatus').className = 'page-status ready';
      $('#btnScrape').style.display = '';
      $('#btnScrape').disabled = false;
      $('#btnScrape').textContent = 'Start Scraping';
      $('#btnStop').style.display = 'none';
      $('#progress').style.display = 'none';
    });
  } catch (err) {
    $('#pageStatus').textContent = 'Error checking page status.';
    $('#pageStatus').className = 'page-status error';
  }
}

checkPageStatus();

// Poll status every 2 seconds (since page reloads kill message listeners)
const statusInterval = setInterval(checkPageStatus, 2000);

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

  // Clear previous state first
  chrome.tabs.sendMessage(tab.id, { type: 'CLEAR_STATE' }, () => {
    chrome.tabs.sendMessage(tab.id, {
      type: 'START_SCRAPE',
      maxPages: settings.maxPages,
      searchName: settings.searchName
    });
  });
});

// Stop scraping
$('#btnStop').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;
  chrome.tabs.sendMessage(tab.id, { type: 'STOP_SCRAPE' });
});

// Send leads to server
$('#btnSend').addEventListener('click', async () => {
  if (collectedLeads.length === 0) return;

  $('#btnSend').disabled = true;
  $('#btnSend').textContent = 'Sending...';
  $('#sendResult').style.display = 'none';

  try {
    const resp = await fetch(settings.apiUrl + '/api/leads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        leads: collectedLeads,
        search_name: settings.searchName
      })
    });

    const data = await resp.json();

    if (resp.ok) {
      $('#statNew').textContent = data.new || 0;
      $('#statDupes').textContent = data.duplicates || 0;
      $('#sendResult').textContent = `✓ Sent! ${data.new || 0} new leads added, ${data.duplicates || 0} duplicates skipped.`;
      $('#sendResult').className = 'send-result success';

      // Clear scrape state after successful send
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab) chrome.tabs.sendMessage(tab.id, { type: 'CLEAR_STATE' });
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

// Refresh server connection periodically
setInterval(checkServerConnection, 30000);
