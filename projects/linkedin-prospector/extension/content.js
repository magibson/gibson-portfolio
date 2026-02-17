// Jarvis Prospector — Content Script
// Runs on LinkedIn Sales Navigator pages
// Scrapes lead cards and handles auto-pagination

(function () {
  'use strict';

  let isScriping = false;
  let shouldStop = false;
  let scrapedLeads = [];

  // Random delay between min and max ms (human-like)
  function randomDelay(minMs = 2000, maxMs = 5000) {
    const delay = Math.floor(Math.random() * (maxMs - minMs + 1)) + minMs;
    return new Promise(resolve => setTimeout(resolve, delay));
  }

  // Detect if we're on a Sales Nav search results page
  function isSearchResultsPage() {
    const url = window.location.href;
    return url.includes('/sales/search/people') || url.includes('/sales/search/company') || url.includes('/sales/lists/');
  }

  // Get total number of pages from the pagination
  function getTotalPages() {
    // Try multiple pagination selectors for Sales Nav
    const selectors = [
      'button.artdeco-pagination__indicator--number span',
      'li.artdeco-pagination__indicator--number button span',
      'li.artdeco-pagination__indicator--number span',
      '[class*="pagination"] li[class*="indicator--number"] span',
      '[class*="pagination"] button[class*="indicator"] span',
      // Sales Nav 2026 selectors
      'button[aria-label*="Page"] span',
      'ol[class*="pagination"] li button span',
      'nav[aria-label*="pagination"] button span',
      'nav[aria-label*="Pagination"] button span'
    ];
    
    for (const sel of selectors) {
      const buttons = document.querySelectorAll(sel);
      if (buttons.length > 0) {
        const last = buttons[buttons.length - 1];
        const num = parseInt(last.textContent.trim(), 10);
        if (num > 0) return num;
      }
    }

    // Fallback: check for "of X" text in pagination area  
    const pagArea = document.querySelector('[class*="pagination"], nav[aria-label*="pagination"], nav[aria-label*="Pagination"]');
    if (pagArea) {
      const match = pagArea.textContent.match(/of\s+(\d+)/i);
      if (match) return parseInt(match[1], 10);
    }

    // Fallback: count from total results / 25 per page
    const totalText = document.querySelector('[class*="search-results__total"], [class*="result-count"]');
    if (totalText) {
      const match = totalText.textContent.match(/(\d[\d,]*)/);
      if (match) {
        const total = parseInt(match[1].replace(/,/g, ''), 10);
        return Math.ceil(total / 25);
      }
    }

    return 1;
  }

  // Get current page number
  function getCurrentPage() {
    const active = document.querySelector('button.artdeco-pagination__indicator--number.active span, li.artdeco-pagination__indicator--number.active button span, [class*="pagination"] [class*="active"] span');
    if (active) return parseInt(active.textContent.trim(), 10) || 1;
    // Fallback: URL param
    const url = new URL(window.location.href);
    const page = url.searchParams.get('page');
    return page ? parseInt(page, 10) : 1;
  }

  // Extract text from element or return empty string
  function getText(el, selector) {
    if (!el) return '';
    const target = selector ? el.querySelector(selector) : el;
    return target ? target.textContent.trim() : '';
  }

  // Scrape all visible lead cards on the current page
  function scrapeCurrentPage() {
    const leads = [];

    // Primary selectors for Sales Nav lead results
    const resultCards = document.querySelectorAll(
      'li.artdeco-list__item, ' +
      '[data-view-name="search-results-lead-card"], ' +
      'ol.artdeco-list li, ' +
      '.search-results__result-list li, ' +
      '[class*="search-results"] li[class*="artdeco"]'
    );

    resultCards.forEach(card => {
      try {
        // Name — multiple possible selectors
        const name =
          getText(card, '[data-anonymize="person-name"]') ||
          getText(card, '.artdeco-entity-lockup__title a span') ||
          getText(card, 'a[data-control-name="view_lead_panel_via_search_lead_name"] span') ||
          getText(card, '.result-lockup__name a') ||
          getText(card, 'dt a span');

        if (!name) return; // Skip if no name found

        // Title / headline
        const title =
          getText(card, '[data-anonymize="title"]') ||
          getText(card, '.artdeco-entity-lockup__subtitle span') ||
          getText(card, '.result-lockup__highlight-keyword') ||
          getText(card, 'dd[class*="lockup__subtitle"] span');

        // Company
        const company =
          getText(card, '[data-anonymize="company-name"]') ||
          getText(card, 'a[data-control-name="view_lead_panel_via_search_lead_company_name"]') ||
          getText(card, '.result-lockup__misc-item a') ||
          '';

        // Location
        const location =
          getText(card, '[data-anonymize="location"]') ||
          getText(card, '.artdeco-entity-lockup__caption span') ||
          getText(card, '.result-lockup__misc-item:not(:has(a))') ||
          '';

        // Profile URL
        let profileUrl = '';
        const profileLink = card.querySelector(
          'a[href*="/sales/lead/"], ' +
          'a[href*="/sales/people/"], ' +
          '.artdeco-entity-lockup__title a, ' +
          'a[data-control-name="view_lead_panel_via_search_lead_name"]'
        );
        if (profileLink) {
          profileUrl = profileLink.href || '';
          // Clean up URL
          if (profileUrl && !profileUrl.startsWith('http')) {
            profileUrl = 'https://www.linkedin.com' + profileUrl;
          }
        }

        // Connection degree
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

        // Time in role
        const timeInRole = (() => {
          const spans = card.querySelectorAll('span, dd');
          for (const s of spans) {
            const t = s.textContent.trim();
            if (/\d+\s*(yr|year|mo|month)/i.test(t) && /in\s*(role|position|current)/i.test(t)) {
              return t;
            }
            if (/^\d+\s*(yr|year|mo|month)/i.test(t)) return t;
          }
          return '';
        })();

        // Profile image
        const img = card.querySelector('img[src*="profile"], img.artdeco-entity-lockup__image, img[class*="presence"]');
        const profileImageUrl = img ? img.src : '';

        // Tags / labels (e.g., "Saved", "Viewed", premium badge)
        const tags = [];
        card.querySelectorAll('[class*="tag"], [class*="badge"], [class*="label"]').forEach(el => {
          const t = el.textContent.trim();
          if (t && t.length < 30) tags.push(t);
        });

        leads.push({
          name,
          title,
          company,
          location,
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

  // Click to the next page
  async function goToNextPage() {
    // Scroll to bottom first so pagination is visible
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    await randomDelay(1000, 2000);

    // Method 1: Find any element containing "Next" text in the pagination area
    const allElements = document.querySelectorAll('button, a');
    for (const el of allElements) {
      const text = el.textContent.trim();
      if (text === 'Next' || text === 'Next >' || text === 'Next›') {
        if (!el.disabled && !el.classList.contains('disabled') && !el.getAttribute('aria-disabled')) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          await randomDelay(500, 1000);
          el.click();
          await randomDelay(3000, 6000);
          await waitForResults();
          return true;
        }
      }
    }

    // Method 2: Try specific selectors
    const selectors = [
      'button.artdeco-pagination__button--next',
      'button[aria-label="Next"]',
      'button[class*="pagination__button--next"]',
      'li.artdeco-pagination__indicator--next button'
    ];

    for (const sel of selectors) {
      const btn = document.querySelector(sel);
      if (btn && !btn.disabled) {
        btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
        await randomDelay(500, 1000);
        btn.click();
        await randomDelay(3000, 6000);
        await waitForResults();
        return true;
      }
    }

    // Method 3: Find the current active page number and click the next one
    const pageButtons = document.querySelectorAll('button');
    let foundActive = false;
    for (const btn of pageButtons) {
      const text = btn.textContent.trim();
      if (foundActive && /^\d+$/.test(text)) {
        // This is the next page number button
        btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
        await randomDelay(500, 1000);
        btn.click();
        await randomDelay(3000, 6000);
        await waitForResults();
        return true;
      }
      // Check if this is the active/selected page
      if (/^\d+$/.test(text) && (
        btn.classList.contains('active') || 
        btn.classList.contains('selected') ||
        btn.getAttribute('aria-current') === 'true' ||
        btn.style.fontWeight === 'bold' ||
        getComputedStyle(btn).fontWeight >= 600
      )) {
        foundActive = true;
      }
    }

    // Method 4: Fallback — increment page in URL
    const url = new URL(window.location.href);
    const currentPage = parseInt(url.searchParams.get('page') || '1', 10);
    const totalPages = getTotalPages();
    if (currentPage < totalPages) {
      url.searchParams.set('page', currentPage + 1);
      window.location.href = url.toString();
      await randomDelay(4000, 7000);
      await waitForResults();
      return true;
    }

    return false;
  }

  // Wait for search results to load
  function waitForResults(timeoutMs = 10000) {
    return new Promise((resolve) => {
      const start = Date.now();
      const check = () => {
        const results = document.querySelectorAll(
          'li.artdeco-list__item, [data-view-name="search-results-lead-card"], ol.artdeco-list li'
        );
        if (results.length > 0 || Date.now() - start > timeoutMs) {
          resolve();
        } else {
          setTimeout(check, 500);
        }
      };
      check();
    });
  }

  // Main scrape function — scrapes all pages
  async function scrapeAllPages(maxPages = 0) {
    isScriping = true;
    shouldStop = false;
    scrapedLeads = [];

    await waitForResults();

    const totalPages = getTotalPages();
    const pagesToScrape = maxPages > 0 ? Math.min(maxPages, totalPages) : totalPages;
    let currentPage = getCurrentPage();

    for (let i = 0; i < pagesToScrape && !shouldStop; i++) {
      // Scrape current page
      const pageLeads = scrapeCurrentPage();
      scrapedLeads = scrapedLeads.concat(pageLeads);

      // Report progress
      chrome.runtime.sendMessage({
        type: 'SCRAPE_PROGRESS',
        data: {
          currentPage: currentPage,
          totalPages: pagesToScrape,
          leadsFound: scrapedLeads.length,
          pageLeads: pageLeads.length
        }
      });

      // If not the last page, navigate to next
      if (i < pagesToScrape - 1) {
        await randomDelay(2000, 5000); // Human-like delay
        const hasNext = await goToNextPage();
        if (!hasNext) break;
        currentPage++;
      }
    }

    isScriping = false;

    // Send final results
    chrome.runtime.sendMessage({
      type: 'SCRAPE_COMPLETE',
      data: {
        leads: scrapedLeads,
        totalPages: pagesToScrape,
        totalLeads: scrapedLeads.length
      }
    });

    return scrapedLeads;
  }

  // Listen for messages from popup
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'START_SCRAPE') {
      if (isScriping) {
        sendResponse({ status: 'already_scraping' });
        return;
      }
      if (!isSearchResultsPage()) {
        sendResponse({ status: 'not_search_page' });
        return;
      }
      sendResponse({ status: 'started' });
      scrapeAllPages(msg.maxPages || 0);
    }

    else if (msg.type === 'STOP_SCRAPE') {
      shouldStop = true;
      sendResponse({ status: 'stopping' });
    }

    else if (msg.type === 'GET_STATUS') {
      sendResponse({
        isSearchPage: isSearchResultsPage(),
        isScraping: isScriping,
        leadsFound: scrapedLeads.length
      });
    }

    else if (msg.type === 'SCRAPE_CURRENT_PAGE_ONLY') {
      const leads = scrapeCurrentPage();
      sendResponse({ leads });
    }

    return true; // Keep message channel open for async
  });

  console.log('[Jarvis Prospector] Content script loaded on Sales Navigator');
})();
