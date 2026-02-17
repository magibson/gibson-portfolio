// Jarvis Prospector — Popup Script

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

// Check current tab status
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
      if (resp.isSearchPage) {
        $('#pageStatus').textContent = resp.isScraping
          ? `Scraping in progress... (${resp.leadsFound} leads)`
          : 'Ready to scrape this search.';
        $('#pageStatus').className = 'page-status ready';
        $('#btnScrape').disabled = resp.isScraping;
        if (resp.isScraping) {
          $('#btnStop').style.display = '';
          $('#btnScrape').style.display = 'none';
        }
      } else {
        $('#pageStatus').textContent = 'This is not a search results page.';
        $('#pageStatus').className = 'page-status error';
        $('#btnScrape').disabled = true;
      }
    });
  } catch (err) {
    $('#pageStatus').textContent = 'Error checking page status.';
    $('#pageStatus').className = 'page-status error';
  }
}

checkPageStatus();

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

  chrome.tabs.sendMessage(tab.id, {
    type: 'START_SCRAPE',
    maxPages: settings.maxPages
  });
});

// Stop scraping
$('#btnStop').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;
  chrome.tabs.sendMessage(tab.id, { type: 'STOP_SCRAPE' });
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'SCRAPE_PROGRESS') {
    const d = msg.data;
    const pct = Math.round((d.currentPage / d.totalPages) * 100);
    $('#progressFill').style.width = pct + '%';
    $('#progressText').textContent = `Scraping page ${d.currentPage} of ${d.totalPages}... (${d.leadsFound} leads found)`;
  }

  else if (msg.type === 'SCRAPE_COMPLETE') {
    const d = msg.data;
    collectedLeads = d.leads;

    // Tag leads with search name
    if (settings.searchName) {
      collectedLeads.forEach(l => l.search_name = settings.searchName);
    }

    $('#btnScrape').style.display = '';
    $('#btnScrape').disabled = false;
    $('#btnStop').style.display = 'none';
    $('#progress').style.display = 'none';
    $('#stats').style.display = 'flex';
    $('#statLeads').textContent = d.totalLeads;
    $('#btnSend').disabled = d.totalLeads === 0;
  }
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

// Refresh status periodically
setInterval(checkServerConnection, 30000);
