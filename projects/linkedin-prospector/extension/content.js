// Jarvis Prospector — Content Script
// URL-based pagination with chrome.storage.local for state persistence

(function () {
  'use strict';

  const STORAGE_KEY = 'jarvisScrapeState';
  const RESULTS_PER_PAGE = 25;

  function randomDelay(minMs = 2000, maxMs = 5000) {
    const delay = Math.floor(Math.random() * (maxMs - minMs + 1)) + minMs;
    return new Promise(resolve => setTimeout(resolve, delay));
  }

  function isSearchResultsPage() {
    const url = window.location.href;
    return url.includes('/sales/search/people') || url.includes('/sales/search/company') || url.includes('/sales/lists/');
  }

  function getCurrentPageFromUrl() {
    const url = new URL(window.location.href);
    return parseInt(url.searchParams.get('page') || '1', 10);
  }

  function getText(el, selector) {
    if (!el) return '';
    const target = selector ? el.querySelector(selector) : el;
    return target ? target.textContent.trim() : '';
  }

  // Detect total pages from the page content
  function detectTotalPages() {
    // Method 1: Look for total results count text like "64 results" or "1-25 of 64"
    const allText = document.body.innerText;

    // Match "X results" pattern
    let match = allText.match(/(\d[\d,]*)\s+results?/i);
    if (match) {
      const total = parseInt(match[1].replace(/,/g, ''), 10);
      if (total > 0) return Math.ceil(total / RESULTS_PER_PAGE);
    }

    // Match "of X" pattern (e.g., "1-25 of 64")
    match = allText.match(/of\s+(\d[\d,]*)/i);
    if (match) {
      const total = parseInt(match[1].replace(/,/g, ''), 10);
      if (total > 0) return Math.ceil(total / RESULTS_PER_PAGE);
    }

    // Method 2: Find highest page number in pagination buttons
    const buttons = document.querySelectorAll('button, a');
    let maxPage = 1;
    for (const btn of buttons) {
      const t = btn.textContent.trim();
      if (/^\d+$/.test(t)) {
        const n = parseInt(t, 10);
        // Only consider reasonable page numbers (< 100) near pagination area
        if (n > maxPage && n < 100) {
          const parent = btn.closest('nav, [class*="pagination"], ol, ul');
          if (parent) maxPage = n;
        }
      }
    }
    if (maxPage > 1) return maxPage;

    return 1;
  }

  function waitForResults(timeoutMs = 15000) {
    return new Promise((resolve) => {
      const start = Date.now();
      const check = () => {
        const results = document.querySelectorAll(
          'li.artdeco-list__item, [data-view-name="search-results-lead-card"], ol.artdeco-list li, .search-results__result-list li'
        );
        if (results.length > 0 || Date.now() - start > timeoutMs) {
          resolve(results.length > 0);
        } else {
          setTimeout(check, 500);
        }
      };
      check();
    });
  }

  function scrapeCurrentPage() {
    const leads = [];
    const resultCards = document.querySelectorAll(
      'li.artdeco-list__item, ' +
      '[data-view-name="search-results-lead-card"], ' +
      'ol.artdeco-list li, ' +
      '.search-results__result-list li, ' +
      '[class*="search-results"] li[class*="artdeco"]'
    );

    resultCards.forEach(card => {
      try {
        const name =
          getText(card, '[data-anonymize="person-name"]') ||
          getText(card, '.artdeco-entity-lockup__title a span') ||
          getText(card, 'a[data-control-name="view_lead_panel_via_search_lead_name"] span') ||
          getText(card, '.result-lockup__name a') ||
          getText(card, 'dt a span');

        if (!name) return;

        const title =
          getText(card, '[data-anonymize="title"]') ||
          getText(card, '.artdeco-entity-lockup__subtitle span') ||
          getText(card, '.result-lockup__highlight-keyword') ||
          getText(card, 'dd[class*="lockup__subtitle"] span');

        const company =
          getText(card, '[data-anonymize="company-name"]') ||
          getText(card, 'a[data-control-name="view_lead_panel_via_search_lead_company_name"]') ||
          getText(card, '.result-lockup__misc-item a') || '';

        const location =
          getText(card, '[data-anonymize="location"]') ||
          getText(card, '.artdeco-entity-lockup__caption span') ||
          getText(card, '.result-lockup__misc-item:not(:has(a))') || '';

        let profileUrl = '';
        const profileLink = card.querySelector(
          'a[href*="/sales/lead/"], a[href*="/sales/people/"], .artdeco-entity-lockup__title a, a[data-control-name="view_lead_panel_via_search_lead_name"]'
        );
        if (profileLink) {
          profileUrl = profileLink.href || '';
          if (profileUrl && !profileUrl.startsWith('http')) {
            profileUrl = 'https://www.linkedin.com' + profileUrl;
          }
        }

        const degree =
          getText(card, '.artdeco-entity-lockup__degree, [class*="degree-icon"] + span, .result-lockup__badge span') ||
          (() => {
            const badges = card.querySelectorAll('span');
            for (const b of badges) {
              const t = b.textContent.trim();
              if (/^(1st|2nd|3rd|Out of Network)$/i.test(t)) return t;
            }
            return '';
          })();

        const timeInRole = (() => {
          const spans = card.querySelectorAll('span, dd');
          for (const s of spans) {
            const t = s.textContent.trim();
            if (/\d+\s*(yr|year|mo|month)/i.test(t) && /in\s*(role|position|current)/i.test(t)) return t;
            if (/^\d+\s*(yr|year|mo|month)/i.test(t)) return t;
          }
          return '';
        })();

        const img = card.querySelector('img[src*="profile"], img.artdeco-entity-lockup__image, img[class*="presence"]');
        const profileImageUrl = img ? img.src : '';

        const tags = [];
        card.querySelectorAll('[class*="tag"], [class*="badge"], [class*="label"]').forEach(el => {
          const t = el.textContent.trim();
          if (t && t.length < 30) tags.push(t);
        });

        leads.push({
          name, title, company, location,
          linkedin_url: profileUrl,
          connection_degree: degree,
          time_in_role: timeInRole,
          profile_image_url: profileImageUrl,
          tags: tags.join(', '),
          scraped_at: new Date().toISOString()
        });
      } catch (err) {
        console.warn('[Jarvis] Error scraping card:', err);
      }
    });

    return leads;
  }

  function navigateToPage(pageNum) {
    const url = new URL(window.location.href);
    url.searchParams.set('page', pageNum);
    window.location.href = url.toString();
  }

  // Get current scrape state from storage
  function getState() {
    return new Promise(resolve => {
      chrome.storage.local.get([STORAGE_KEY], result => {
        resolve(result[STORAGE_KEY] || null);
      });
    });
  }

  function setState(state) {
    return new Promise(resolve => {
      chrome.storage.local.set({ [STORAGE_KEY]: state }, resolve);
    });
  }

  function clearState() {
    return new Promise(resolve => {
      chrome.storage.local.remove([STORAGE_KEY], resolve);
    });
  }

  // Continue a multi-page scrape (called on page load if scrape is in progress)
  async function continueScrape() {
    const state = await getState();
    if (!state || !state.inProgress) return;

    console.log(`[Jarvis] Continuing scrape: page ${state.currentPage} of ${state.totalPages}`);

    await waitForResults();
    await randomDelay(1000, 2000); // Extra settle time

    const pageLeads = scrapeCurrentPage();
    const allLeads = (state.leads || []).concat(pageLeads);

    console.log(`[Jarvis] Page ${state.currentPage}: scraped ${pageLeads.length} leads (total: ${allLeads.length})`);

    // Update state with new leads
    const nextPage = state.currentPage + 1;

    if (nextPage > state.totalPages || state.shouldStop) {
      // Done! Save final results and clear in-progress flag
      await setState({
        inProgress: false,
        completed: true,
        leads: allLeads,
        totalPages: state.totalPages,
        totalLeads: allLeads.length,
        maxPages: state.maxPages,
        searchName: state.searchName
      });
      console.log(`[Jarvis] Scrape complete! ${allLeads.length} leads across ${state.totalPages} pages`);
    } else {
      // Save progress and navigate to next page
      await setState({
        ...state,
        currentPage: nextPage,
        leads: allLeads
      });

      // Random delay before navigating (human-like)
      const delay = Math.floor(Math.random() * 3000) + 2000;
      console.log(`[Jarvis] Waiting ${delay}ms before navigating to page ${nextPage}...`);
      await new Promise(r => setTimeout(r, delay));

      navigateToPage(nextPage);
    }
  }

  // Start a new multi-page scrape
  async function startScrape(maxPages = 0, searchName = '') {
    await waitForResults();

    const totalPages = detectTotalPages();
    const pagesToScrape = maxPages > 0 ? Math.min(maxPages, totalPages) : totalPages;
    const currentPage = getCurrentPageFromUrl();

    console.log(`[Jarvis] Starting scrape: page ${currentPage}, total pages: ${pagesToScrape}`);

    if (pagesToScrape <= 1) {
      // Single page — just scrape and done
      const leads = scrapeCurrentPage();
      await setState({
        inProgress: false,
        completed: true,
        leads,
        totalPages: 1,
        totalLeads: leads.length,
        searchName
      });
      console.log(`[Jarvis] Single page scrape complete: ${leads.length} leads`);
      return;
    }

    // Multi-page: scrape current page, save state, navigate
    const pageLeads = scrapeCurrentPage();
    console.log(`[Jarvis] Page ${currentPage}: scraped ${pageLeads.length} leads`);

    const startPage = currentPage;
    const endPage = startPage + pagesToScrape - 1;
    const nextPage = currentPage + 1;

    if (nextPage > endPage) {
      // Already on last page
      await setState({
        inProgress: false,
        completed: true,
        leads: pageLeads,
        totalPages: pagesToScrape,
        totalLeads: pageLeads.length,
        searchName
      });
      return;
    }

    await setState({
      inProgress: true,
      completed: false,
      shouldStop: false,
      currentPage: nextPage,
      totalPages: endPage,
      leads: pageLeads,
      maxPages,
      searchName,
      startedAt: new Date().toISOString()
    });

    // Random delay then navigate
    const delay = Math.floor(Math.random() * 3000) + 2000;
    console.log(`[Jarvis] Waiting ${delay}ms before navigating to page ${nextPage}...`);
    await new Promise(r => setTimeout(r, delay));

    navigateToPage(nextPage);
  }

  // Listen for messages from popup
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'START_SCRAPE') {
      if (!isSearchResultsPage()) {
        sendResponse({ status: 'not_search_page' });
        return;
      }
      // Check if already in progress
      getState().then(state => {
        if (state && state.inProgress) {
          sendResponse({ status: 'already_scraping' });
          return;
        }
        sendResponse({ status: 'started' });
        startScrape(msg.maxPages || 0, msg.searchName || '');
      });
      return true;
    }

    else if (msg.type === 'STOP_SCRAPE') {
      getState().then(async state => {
        if (state && state.inProgress) {
          await setState({ ...state, shouldStop: true });
        }
        sendResponse({ status: 'stopping' });
      });
      return true;
    }

    else if (msg.type === 'GET_STATUS') {
      getState().then(state => {
        sendResponse({
          isSearchPage: isSearchResultsPage(),
          isScraping: state ? state.inProgress : false,
          completed: state ? state.completed : false,
          leadsFound: state ? (state.leads || []).length : 0,
          totalPages: state ? state.totalPages : 0,
          currentPage: state ? state.currentPage : 0,
          leads: (state && state.completed) ? state.leads : null,
          totalLeads: state ? state.totalLeads : 0,
          searchName: state ? state.searchName : ''
        });
      });
      return true;
    }

    else if (msg.type === 'CLEAR_STATE') {
      clearState().then(() => sendResponse({ status: 'cleared' }));
      return true;
    }

    else if (msg.type === 'SCRAPE_CURRENT_PAGE_ONLY') {
      const leads = scrapeCurrentPage();
      sendResponse({ leads });
    }

    return true;
  });

  // On load: check if we need to continue a multi-page scrape
  if (isSearchResultsPage()) {
    continueScrape();
  }

  console.log('[Jarvis Prospector] Content script loaded on Sales Navigator');
})();
