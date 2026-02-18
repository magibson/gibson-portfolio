// Jarvis Prospector — Content Script
// Bulletproof URL-based pagination with chrome.storage.local

(function () {
  'use strict';

  const STORAGE_KEY = 'jarvisScrapeState';
  const RESULTS_PER_PAGE = 25;
  const MAX_WAIT_FOR_RESULTS_MS = 20000;
  const POLL_INTERVAL_MS = 500;

  console.log('[Jarvis] Content script LOADED. URL:', window.location.href, 'readyState:', document.readyState);

  function randomDelay(minMs = 2000, maxMs = 5000) {
    return new Promise(resolve => setTimeout(resolve, Math.floor(Math.random() * (maxMs - minMs + 1)) + minMs));
  }

  function isSearchResultsPage() {
    const url = window.location.href;
    return url.includes('/sales/search/people') || url.includes('/sales/search/company') || url.includes('/sales/lists/');
  }

  function detectSearchName() {
    const selectors = ['h1', '.search-results-container h1', '[class*="search-title"]', '[class*="saved-search"] span'];
    for (const sel of selectors) {
      const els = document.querySelectorAll(sel);
      for (const el of els) {
        const t = el.textContent.trim();
        if (t && t.length > 2 && t.length < 60 && !t.includes('results') && !t.includes('Search')) return t;
      }
    }
    return '';
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

  function detectTotalPages() {
    const allText = document.body.innerText;

    // "X results"
    let match = allText.match(/(\d[\d,]*)\s+results?/i);
    if (match) {
      const total = parseInt(match[1].replace(/,/g, ''), 10);
      console.log('[Jarvis] detectTotalPages: found "X results" =', total);
      if (total > 0) return Math.ceil(total / RESULTS_PER_PAGE);
    }

    // "of X"
    match = allText.match(/of\s+(\d[\d,]*)/i);
    if (match) {
      const total = parseInt(match[1].replace(/,/g, ''), 10);
      console.log('[Jarvis] detectTotalPages: found "of X" =', total);
      if (total > 0) return Math.ceil(total / RESULTS_PER_PAGE);
    }

    // Pagination buttons
    const buttons = document.querySelectorAll('button, a');
    let maxPage = 1;
    for (const btn of buttons) {
      const t = btn.textContent.trim();
      if (/^\d+$/.test(t)) {
        const n = parseInt(t, 10);
        if (n > maxPage && n < 100) {
          const parent = btn.closest('nav, [class*="pagination"], ol, ul');
          if (parent) maxPage = n;
        }
      }
    }
    if (maxPage > 1) {
      console.log('[Jarvis] detectTotalPages: pagination buttons max =', maxPage);
      return maxPage;
    }

    console.log('[Jarvis] detectTotalPages: could not detect, returning 1');
    return 1;
  }

  // Robust wait: polls for result elements, uses MutationObserver as backup
  function waitForResults(timeoutMs = MAX_WAIT_FOR_RESULTS_MS) {
    return new Promise((resolve) => {
      const SELECTORS = 'li.artdeco-list__item, [data-view-name="search-results-lead-card"], ol.artdeco-list li, .search-results__result-list li';

      const getResults = () => document.querySelectorAll(SELECTORS);

      // Check immediately
      if (getResults().length > 0) {
        console.log('[Jarvis] waitForResults: results already present:', getResults().length);
        resolve(true);
        return;
      }

      let resolved = false;
      const done = (found) => {
        if (resolved) return;
        resolved = true;
        if (observer) observer.disconnect();
        clearTimeout(timer);
        clearInterval(poller);
        resolve(found);
      };

      // Polling
      const poller = setInterval(() => {
        const r = getResults();
        if (r.length > 0) {
          console.log('[Jarvis] waitForResults: poll found', r.length, 'results');
          done(true);
        }
      }, POLL_INTERVAL_MS);

      // MutationObserver backup
      let observer = null;
      try {
        observer = new MutationObserver(() => {
          const r = getResults();
          if (r.length > 0) {
            console.log('[Jarvis] waitForResults: MutationObserver found', r.length, 'results');
            done(true);
          }
        });
        observer.observe(document.body, { childList: true, subtree: true });
      } catch (e) {
        console.warn('[Jarvis] MutationObserver failed:', e);
      }

      // Timeout
      const timer = setTimeout(() => {
        const r = getResults();
        console.log('[Jarvis] waitForResults: TIMEOUT after', timeoutMs, 'ms. Results found:', r.length);
        done(r.length > 0);
      }, timeoutMs);
    });
  }

  // Scroll to bottom and back to trigger lazy-loaded results
  async function scrollToLoadAllResults() {
    console.log('[Jarvis] Scrolling to load all results...');
    const delay = ms => new Promise(r => setTimeout(r, ms));
    const scrollHeight = document.body.scrollHeight;
    // Scroll down in increments
    for (let y = 0; y <= scrollHeight; y += 400) {
      window.scrollTo(0, y);
      await delay(150);
    }
    await delay(800);
    // Scroll back to top
    window.scrollTo(0, 0);
    await delay(500);
    console.log('[Jarvis] Scroll complete');
  }

  function scrapeCurrentPage() {
    const leads = [];
    const resultCards = document.querySelectorAll(
      'li.artdeco-list__item, [data-view-name="search-results-lead-card"], ol.artdeco-list li, .search-results__result-list li, [class*="search-results"] li[class*="artdeco"]'
    );

    console.log('[Jarvis] scrapeCurrentPage: found', resultCards.length, 'cards');

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
          if (profileUrl && !profileUrl.startsWith('http')) profileUrl = 'https://www.linkedin.com' + profileUrl;
        }

        const degree =
          getText(card, '.artdeco-entity-lockup__degree, [class*="degree-icon"] + span, .result-lockup__badge span') ||
          (() => {
            for (const b of card.querySelectorAll('span')) {
              const t = b.textContent.trim();
              if (/^(1st|2nd|3rd|Out of Network)$/i.test(t)) return t;
            }
            return '';
          })();

        const timeInRole = (() => {
          for (const s of card.querySelectorAll('span, dd')) {
            const t = s.textContent.trim();
            if (/\d+\s*(yr|year|mo|month)/i.test(t)) return t;
          }
          return '';
        })();

        const img = card.querySelector('img[src*="profile"], img.artdeco-entity-lockup__image, img[class*="presence"]');

        leads.push({
          name, title, company, location,
          linkedin_url: profileUrl,
          connection_degree: degree,
          time_in_role: timeInRole,
          profile_image_url: img ? img.src : '',
          tags: '',
          scraped_at: new Date().toISOString()
        });
      } catch (err) {
        console.warn('[Jarvis] Error scraping card:', err);
      }
    });

    console.log('[Jarvis] scrapeCurrentPage: extracted', leads.length, 'leads with names');
    return leads;
  }

  function navigateToPage(pageNum) {
    const url = new URL(window.location.href);
    url.searchParams.set('page', String(pageNum));
    const target = url.toString();
    console.log('[Jarvis] Navigating to:', target);
    window.location.href = target;
  }

  function getState() {
    return new Promise(resolve => {
      chrome.storage.local.get([STORAGE_KEY], result => resolve(result[STORAGE_KEY] || null));
    });
  }

  function setState(state) {
    console.log('[Jarvis] setState:', JSON.stringify({ ...state, leads: `[${(state.leads || []).length} leads]` }));
    return new Promise(resolve => {
      chrome.storage.local.set({ [STORAGE_KEY]: state }, resolve);
    });
  }

  function clearState() {
    return new Promise(resolve => chrome.storage.local.remove([STORAGE_KEY], resolve));
  }

  // Continue a multi-page scrape after page reload
  async function continueScrape() {
    const state = await getState();
    if (!state || !state.inProgress) {
      console.log('[Jarvis] continueScrape: no active state, aborting');
      return;
    }

    // Check shouldStop
    if (state.shouldStop) {
      console.log('[Jarvis] continueScrape: shouldStop flag set, finalizing');
      await setState({
        inProgress: false, completed: true,
        leads: state.leads || [], totalPages: state.totalPages,
        totalLeads: (state.leads || []).length, searchName: state.searchName
      });
      return;
    }

    const expectedPage = state.currentPage;
    const actualPage = getCurrentPageFromUrl();
    console.log('[Jarvis] continueScrape: expected page', expectedPage, 'actual URL page', actualPage);

    // Verify we're on the right page
    if (actualPage !== expectedPage) {
      console.warn('[Jarvis] Page mismatch! Expected', expectedPage, 'got', actualPage, '- navigating to correct page');
      navigateToPage(expectedPage);
      return;
    }

    // Wait for results with generous timeout
    console.log('[Jarvis] continueScrape: waiting for results (up to', MAX_WAIT_FOR_RESULTS_MS, 'ms)...');
    const found = await waitForResults(MAX_WAIT_FOR_RESULTS_MS);

    if (!found) {
      console.warn('[Jarvis] continueScrape: NO results found after waiting. Stopping.');
      await setState({
        inProgress: false, completed: true,
        leads: state.leads || [], totalPages: state.totalPages,
        totalLeads: (state.leads || []).length, searchName: state.searchName
      });
      return;
    }

    // Extra settle time for Sales Nav's lazy rendering
    console.log('[Jarvis] continueScrape: results detected, waiting 3s for full render...');
    await new Promise(r => setTimeout(r, 3000));

    // Scroll to trigger lazy-loaded results before scraping
    await scrollToLoadAllResults();

    // Scrape
    const pageLeads = scrapeCurrentPage();
    const allLeads = (state.leads || []).concat(pageLeads);

    console.log('[Jarvis] continueScrape: page', expectedPage, 'scraped', pageLeads.length, 'leads. Total:', allLeads.length);

    const nextPage = expectedPage + 1;

    // Re-check shouldStop (might have been set during our wait)
    const freshState = await getState();
    const shouldStop = freshState && freshState.shouldStop;

    if (nextPage > state.totalPages || shouldStop || pageLeads.length === 0) {
      console.log('[Jarvis] Scrape COMPLETE.', allLeads.length, 'total leads.',
        nextPage > state.totalPages ? '(past last page)' : '',
        shouldStop ? '(stopped by user)' : '',
        pageLeads.length === 0 ? '(empty page)' : '');

      await setState({
        inProgress: false, completed: true,
        leads: allLeads, totalPages: state.totalPages,
        totalLeads: allLeads.length, searchName: state.searchName
      });
    } else {
      // Save progress and navigate
      await setState({
        ...state,
        currentPage: nextPage,
        leads: allLeads
      });

      const delay = Math.floor(Math.random() * 3000) + 2000;
      console.log('[Jarvis] Waiting', delay, 'ms before navigating to page', nextPage);
      await new Promise(r => setTimeout(r, delay));

      navigateToPage(nextPage);
    }
  }

  // Start a new scrape
  async function startScrape(maxPages = 0, searchName = '') {
    console.log('[Jarvis] startScrape called. maxPages:', maxPages, 'searchName:', searchName);

    // Clear any old state first
    await clearState();

    // Wait for results
    const found = await waitForResults(MAX_WAIT_FOR_RESULTS_MS);
    if (!found) {
      console.warn('[Jarvis] startScrape: no results found on page');
      await setState({ inProgress: false, completed: true, leads: [], totalPages: 0, totalLeads: 0, searchName });
      return;
    }

    // Extra settle
    await new Promise(r => setTimeout(r, 2000));

    if (!searchName) searchName = detectSearchName();

    let totalPages = detectTotalPages();
    const currentPage = getCurrentPageFromUrl();

    if (totalPages <= 1 && maxPages > 0) totalPages = maxPages;
    else if (totalPages <= 1) totalPages = 20; // generous default, stops on empty page

    const pagesToScrape = maxPages > 0 ? Math.min(maxPages, totalPages) : totalPages;
    console.log('[Jarvis] startScrape: currentPage', currentPage, 'totalPages', totalPages, 'pagesToScrape', pagesToScrape);

    // Scroll to load lazy results before first page scrape
    await scrollToLoadAllResults();

    const pageLeads = scrapeCurrentPage();
    console.log('[Jarvis] startScrape: page', currentPage, 'scraped', pageLeads.length, 'leads');

    if (pageLeads.length === 0) {
      await setState({ inProgress: false, completed: true, leads: [], totalPages: 0, totalLeads: 0, searchName });
      return;
    }

    const endPage = currentPage + pagesToScrape - 1;
    const nextPage = currentPage + 1;

    if (nextPage > endPage) {
      // Single page only
      await setState({ inProgress: false, completed: true, leads: pageLeads, totalPages: 1, totalLeads: pageLeads.length, searchName });
      console.log('[Jarvis] Single page scrape complete:', pageLeads.length, 'leads');
      return;
    }

    // Multi-page: save state and navigate
    await setState({
      inProgress: true, completed: false, shouldStop: false,
      currentPage: nextPage, totalPages: endPage,
      leads: pageLeads, maxPages, searchName,
      startedAt: new Date().toISOString()
    });

    const delay = Math.floor(Math.random() * 3000) + 2000;
    console.log('[Jarvis] Waiting', delay, 'ms before navigating to page', nextPage);
    await new Promise(r => setTimeout(r, delay));

    navigateToPage(nextPage);
  }

  // Message listener
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    console.log('[Jarvis] Message received:', msg.type);

    if (msg.type === 'START_SCRAPE') {
      if (!isSearchResultsPage()) {
        sendResponse({ status: 'not_search_page' });
        return;
      }
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

    if (msg.type === 'STOP_SCRAPE') {
      getState().then(async state => {
        if (state && state.inProgress) {
          await setState({ ...state, shouldStop: true });
          console.log('[Jarvis] Stop requested');
        }
        sendResponse({ status: 'stopping' });
      });
      return true;
    }

    if (msg.type === 'GET_STATUS') {
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

    if (msg.type === 'CLEAR_STATE') {
      clearState().then(() => sendResponse({ status: 'cleared' }));
      return true;
    }

    if (msg.type === 'SCRAPE_CURRENT_PAGE_ONLY') {
      const leads = scrapeCurrentPage();
      sendResponse({ leads });
    }

    return true;
  });

  // ON LOAD: check for in-progress scrape to continue
  // Use a robust approach: wait for document to be fully loaded, then check state
  function initOnLoad() {
    if (!isSearchResultsPage()) {
      console.log('[Jarvis] Not a search results page, skipping auto-resume');
      return;
    }

    console.log('[Jarvis] Search results page detected. Checking for in-progress scrape...');

    getState().then(state => {
      console.log('[Jarvis] Current state:', state ? JSON.stringify({ ...state, leads: `[${(state.leads || []).length}]` }) : 'null');
      if (state && state.inProgress) {
        console.log('[Jarvis] IN-PROGRESS scrape found! Resuming in 1s...');
        // Small delay to let the page start rendering
        setTimeout(() => continueScrape(), 1000);
      } else {
        console.log('[Jarvis] No in-progress scrape.');
      }
    });
  }

  // document_idle should mean DOM is ready, but be safe
  if (document.readyState === 'complete') {
    initOnLoad();
  } else {
    window.addEventListener('load', initOnLoad);
  }

})();
