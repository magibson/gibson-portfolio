/**
 * OpenTable Client (Stealth Edition)
 * 
 * Uses browser automation with stealth plugins to evade bot detection.
 * Implements realistic fingerprinting and human-like delays.
 * 
 * Note: OpenTable has aggressive bot detection (Cloudflare).
 * This version uses playwright-extra + stealth plugin.
 */

import { chromium } from 'playwright-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Apply stealth plugin to chromium
chromium.use(StealthPlugin());

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Human-like delay helpers
const randomDelay = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
const humanDelay = () => new Promise(r => setTimeout(r, randomDelay(800, 2500)));
const shortDelay = () => new Promise(r => setTimeout(r, randomDelay(200, 600)));
const typeDelay = () => new Promise(r => setTimeout(r, randomDelay(50, 150)));

class OpenTableClient {
  constructor(configPath = path.join(__dirname, 'config.json')) {
    this.baseUrl = 'https://www.opentable.com';
    this.configPath = configPath;
    this.config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    this.browser = null;
    this.context = null;
    this.page = null;
    this.cookiesPath = path.join(__dirname, '.opentable-cookies.json');
  }

  async init() {
    // Realistic browser fingerprint profiles
    const profiles = [
      {
        userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        viewport: { width: 1440, height: 900 },
        locale: 'en-US',
        timezone: 'America/New_York'
      },
      {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 },
        locale: 'en-US',
        timezone: 'America/Chicago'
      },
      {
        userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        viewport: { width: 1680, height: 1050 },
        locale: 'en-US',
        timezone: 'America/Los_Angeles'
      }
    ];
    
    const profile = profiles[Math.floor(Math.random() * profiles.length)];
    
    this.browser = await chromium.launch({ 
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-blink-features=AutomationControlled',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--disable-gpu',
        '--window-size=1920,1080',
        '--start-maximized',
        '--disable-infobars'
      ]
    });
    
    this.context = await this.browser.newContext({
      userAgent: profile.userAgent,
      viewport: profile.viewport,
      locale: profile.locale,
      timezoneId: profile.timezone,
      deviceScaleFactor: 2,
      hasTouch: false,
      isMobile: false,
      permissions: ['geolocation'],
      geolocation: { longitude: -73.935242, latitude: 40.730610 }, // NYC
      colorScheme: 'light'
    });
    
    // Enhanced stealth: mask webdriver and add realistic browser properties
    await this.context.addInitScript(() => {
      // Remove webdriver property
      Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
      });
      
      // Mock plugins array (real browsers have plugins)
      Object.defineProperty(navigator, 'plugins', {
        get: () => {
          const plugins = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
            { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
          ];
          plugins.item = (i) => plugins[i] || null;
          plugins.namedItem = (name) => plugins.find(p => p.name === name) || null;
          plugins.refresh = () => {};
          return plugins;
        }
      });
      
      // Mock languages
      Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
      });
      
      // Add chrome object (exists in real Chrome)
      window.chrome = {
        runtime: {
          connect: () => {},
          sendMessage: () => {},
          onMessage: { addListener: () => {} }
        },
        loadTimes: () => ({
          requestTime: Date.now() / 1000 - Math.random() * 100,
          startLoadTime: Date.now() / 1000 - Math.random() * 50,
          commitLoadTime: Date.now() / 1000 - Math.random() * 30,
          finishDocumentLoadTime: Date.now() / 1000 - Math.random() * 10,
          finishLoadTime: Date.now() / 1000
        }),
        csi: () => ({ pageT: Date.now() })
      };
      
      // Mock permissions API
      const originalQuery = window.navigator.permissions?.query;
      if (originalQuery) {
        window.navigator.permissions.query = (parameters) => {
          if (parameters.name === 'notifications') {
            return Promise.resolve({ state: Notification.permission, onchange: null });
          }
          return originalQuery(parameters);
        };
      }
      
      // Mock WebGL vendor/renderer
      const getParameter = WebGLRenderingContext.prototype.getParameter;
      WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.apply(this, arguments);
      };
      
      // Consistent canvas fingerprint
      const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
      HTMLCanvasElement.prototype.toDataURL = function(type) {
        if (type === 'image/png' && this.width === 16 && this.height === 16) {
          // Small canvases often used for fingerprinting
          return originalToDataURL.apply(this, arguments);
        }
        return originalToDataURL.apply(this, arguments);
      };
    });
    
    // Load cookies if they exist
    if (fs.existsSync(this.cookiesPath)) {
      try {
        const cookies = JSON.parse(fs.readFileSync(this.cookiesPath, 'utf8'));
        await this.context.addCookies(cookies);
      } catch (e) {
        console.warn('Warning: Could not load cookies:', e.message);
      }
    }
    
    this.page = await this.context.newPage();
    
    // Add human-like mouse movements and behavior
    this.page.on('domcontentloaded', async () => {
      // Simulate some initial mouse movement after page loads
      try {
        await this.page.mouse.move(
          randomDelay(100, 500),
          randomDelay(100, 300)
        );
      } catch (e) {
        // Ignore errors from closed pages
      }
    });
  }

  async close() {
    if (this.browser) {
      await this.browser.close();
    }
  }

  async saveCookies() {
    const cookies = await this.context.cookies();
    fs.writeFileSync(this.cookiesPath, JSON.stringify(cookies, null, 2));
  }

  // Human-like typing with variable delays
  async humanType(locator, text) {
    await locator.click();
    await shortDelay();
    for (const char of text) {
      await locator.press(char, { delay: randomDelay(50, 150) });
      if (Math.random() < 0.1) {
        await shortDelay(); // Occasional pause while typing
      }
    }
  }

  // Human-like page navigation with Cloudflare handling
  async humanGoto(url, options = {}) {
    console.log(`Navigating to: ${url}`);
    await humanDelay();
    
    // Navigate with just domcontentloaded (doesn't wait for all network)
    await this.page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    
    // Check for Cloudflare challenge and wait it out
    let attempts = 0;
    const maxAttempts = 10;
    
    while (attempts < maxAttempts) {
      const pageContent = await this.page.content();
      const isCloudflareChallenge = pageContent.includes('Just a moment') ||
                                     pageContent.includes('challenge-platform') ||
                                     pageContent.includes('cf-browser-verification') ||
                                     pageContent.includes('Checking your browser');
      
      if (!isCloudflareChallenge) {
        console.log('✓ Passed Cloudflare check');
        break;
      }
      
      attempts++;
      console.log(`Waiting for Cloudflare challenge... (attempt ${attempts}/${maxAttempts})`);
      await new Promise(r => setTimeout(r, 3000)); // Wait 3 seconds between checks
    }
    
    if (attempts >= maxAttempts) {
      console.warn('⚠ Cloudflare challenge may not have completed');
    }
    
    // Try to wait for networkidle but don't fail if it times out
    try {
      await this.page.waitForLoadState('networkidle', { timeout: 15000 });
    } catch (e) {
      console.log('Note: networkidle timeout (continuing anyway)');
    }
    
    await humanDelay();
    
    // Random scroll to appear human
    try {
      await this.page.mouse.wheel(0, randomDelay(100, 300));
    } catch (e) {
      // Ignore scroll errors
    }
    await shortDelay();
  }

  /**
   * Login to OpenTable
   */
  async login(email, password) {
    email = email || this.config.credentials?.opentable?.email;
    password = password || this.config.credentials?.opentable?.password;
    
    if (!email || !password) {
      throw new Error('OpenTable credentials not configured');
    }

    await this.humanGoto(`${this.baseUrl}/sign-in`);
    await this.page.waitForLoadState('networkidle', { timeout: 30000 });
    await humanDelay();
    
    // Fill login form with human-like typing
    const emailInput = this.page.locator('input[name="email"], input[type="email"]').first();
    const passwordInput = this.page.locator('input[name="password"], input[type="password"]').first();
    
    await this.humanType(emailInput, email);
    await humanDelay();
    await this.humanType(passwordInput, password);
    await humanDelay();
    
    // Click sign in
    await this.page.click('button[type="submit"]');
    await this.page.waitForLoadState('networkidle', { timeout: 30000 });
    await humanDelay();
    
    // Check if logged in
    const isLoggedIn = await this.page.locator('[data-test="user-profile-avatar"]').count() > 0 ||
                       await this.page.locator('a[href*="/my/profile"]').count() > 0;
    
    if (isLoggedIn) {
      await this.saveCookies();
      console.log('✅ OpenTable login successful');
      return { success: true };
    }
    
    return { success: false, error: 'Login failed' };
  }

  /**
   * Search for restaurants
   */
  async searchRestaurants(location, date, time, partySize = 2, cuisine = '') {
    // Format: YYYY-MM-DD
    const dateStr = date instanceof Date ? date.toISOString().split('T')[0] : date;
    
    // Build search URL
    const searchUrl = new URL(`${this.baseUrl}/s`);
    searchUrl.searchParams.set('dateTime', `${dateStr}T${time}`);
    searchUrl.searchParams.set('covers', partySize.toString());
    searchUrl.searchParams.set('term', location);
    if (cuisine) {
      searchUrl.searchParams.set('term', `${cuisine} ${location}`);
    }

    await this.humanGoto(searchUrl.toString());
    await this.page.waitForLoadState('networkidle', { timeout: 30000 });
    await humanDelay();

    // Extract restaurant results
    const restaurants = await this.page.evaluate(() => {
      const results = [];
      const cards = document.querySelectorAll('[data-test="restaurant-card"], .restaurant-card, [class*="RestaurantCard"]');
      
      cards.forEach(card => {
        const nameEl = card.querySelector('h2, [class*="name"], [data-test="restaurant-name"]');
        const linkEl = card.querySelector('a[href*="/restaurant"]');
        const ratingEl = card.querySelector('[class*="rating"], [data-test="rating"]');
        const cuisineEl = card.querySelector('[class*="cuisine"], [data-test="cuisine"]');
        const priceEl = card.querySelector('[class*="price"]');
        
        if (nameEl) {
          const href = linkEl?.href || '';
          const idMatch = href.match(/\/restaurant\/[^/]+\/([^/?]+)/);
          
          results.push({
            name: nameEl.textContent?.trim(),
            id: idMatch ? idMatch[1] : href.split('/').pop()?.split('?')[0],
            url: href,
            rating: ratingEl?.textContent?.trim(),
            cuisine: cuisineEl?.textContent?.trim(),
            price: priceEl?.textContent?.trim()
          });
        }
      });
      
      return results;
    });

    return restaurants;
  }

  /**
   * Get availability for a specific restaurant
   */
  async getAvailability(restaurantId, date, time, partySize = 2) {
    const dateStr = date instanceof Date ? date.toISOString().split('T')[0] : date;
    
    // Go to restaurant page with date/time/party
    const url = `${this.baseUrl}/r/${restaurantId}?covers=${partySize}&dateTime=${dateStr}T${time}`;
    await this.humanGoto(url);
    await this.page.waitForLoadState('networkidle', { timeout: 30000 });
    await humanDelay();

    // Extract available time slots
    const slots = await this.page.evaluate(() => {
      const timeSlots = [];
      const slotElements = document.querySelectorAll(
        '[data-test="time-slot"], button[class*="TimeSlot"], [class*="timeslot"]'
      );
      
      slotElements.forEach(slot => {
        const timeText = slot.textContent?.trim();
        if (timeText && /\d{1,2}:\d{2}/.test(timeText)) {
          timeSlots.push({
            time: timeText,
            available: !slot.disabled && !slot.classList.contains('disabled')
          });
        }
      });
      
      return timeSlots;
    });

    return slots;
  }

  /**
   * Make a reservation
   */
  async makeReservation(restaurantId, date, time, partySize = 2) {
    const dateStr = date instanceof Date ? date.toISOString().split('T')[0] : date;
    
    // Navigate to restaurant
    const url = `${this.baseUrl}/r/${restaurantId}?covers=${partySize}&dateTime=${dateStr}T${time}`;
    await this.humanGoto(url);
    await this.page.waitForLoadState('networkidle', { timeout: 30000 });
    await humanDelay();

    // Find and click the time slot
    const timeButton = await this.page.locator(
      `button:has-text("${time}"), [data-test="time-slot"]:has-text("${time}")`
    ).first();
    
    if (!await timeButton.count()) {
      // Try finding any available slot around the requested time
      const availableSlot = await this.page.locator(
        '[data-test="time-slot"]:not([disabled]), button[class*="TimeSlot"]:not([disabled])'
      ).first();
      
      if (!await availableSlot.count()) {
        return { success: false, error: 'No available time slots found' };
      }
      
      await humanDelay();
      await availableSlot.click();
    } else {
      await humanDelay();
      await timeButton.click();
    }

    await this.page.waitForLoadState('networkidle', { timeout: 30000 });
    await humanDelay();

    // Check if we need to fill in guest info
    const userPrefs = this.config.user_preferences;
    
    // Fill phone if required
    const phoneInput = await this.page.locator('input[name="phone"], input[type="tel"]').first();
    if (await phoneInput.count() && userPrefs.phone) {
      await this.humanType(phoneInput, userPrefs.phone.replace(/\D/g, ''));
    }

    // Fill email if required
    const emailInput = await this.page.locator('input[name="email"]:not([disabled])').first();
    if (await emailInput.count() && userPrefs.email) {
      await this.humanType(emailInput, userPrefs.email);
    }

    // Look for special requests/notes field
    const notesInput = await this.page.locator('textarea[name*="note"], textarea[name*="request"]').first();
    if (await notesInput.count()) {
      // Leave empty or add standard note
    }

    await humanDelay();

    // Click complete/confirm reservation
    const confirmButton = await this.page.locator(
      'button[type="submit"]:has-text("Complete"), button:has-text("Confirm"), button:has-text("Reserve")'
    ).first();
    
    if (await confirmButton.count()) {
      await confirmButton.click();
      await this.page.waitForLoadState('networkidle', { timeout: 30000 });
      await humanDelay();

      // Check for confirmation
      const confirmation = await this.page.evaluate(() => {
        const confEl = document.querySelector(
          '[data-test="confirmation-number"], [class*="confirmation"], .confirmation'
        );
        const successEl = document.querySelector('[class*="success"], [data-test="success"]');
        
        return {
          confirmationNumber: confEl?.textContent?.trim(),
          success: !!successEl || document.body.textContent?.includes('confirmed') || 
                   document.body.textContent?.includes('Reservation')
        };
      });

      await this.saveCookies();
      
      return {
        success: confirmation.success,
        confirmation: confirmation.confirmationNumber,
        url: this.page.url()
      };
    }

    return { success: false, error: 'Could not find confirm button' };
  }

  /**
   * Get user's reservations
   */
  async getMyReservations() {
    await this.humanGoto(`${this.baseUrl}/my/reservations/upcoming`);
    await this.page.waitForLoadState('networkidle', { timeout: 30000 });
    await humanDelay();

    const reservations = await this.page.evaluate(() => {
      const results = [];
      const cards = document.querySelectorAll('[data-test="reservation-card"], [class*="reservation"]');
      
      cards.forEach(card => {
        const nameEl = card.querySelector('[class*="name"], h2, h3');
        const dateEl = card.querySelector('[class*="date"], time');
        const timeEl = card.querySelector('[class*="time"]');
        const partySizeEl = card.querySelector('[class*="party"], [class*="covers"]');
        const confEl = card.querySelector('[class*="confirmation"]');
        
        results.push({
          restaurant: nameEl?.textContent?.trim(),
          date: dateEl?.textContent?.trim(),
          time: timeEl?.textContent?.trim(),
          partySize: partySizeEl?.textContent?.trim(),
          confirmationNumber: confEl?.textContent?.trim()
        });
      });
      
      return results;
    });

    return reservations;
  }

  /**
   * Cancel a reservation
   */
  async cancelReservation(confirmationNumber) {
    // Go to reservations page
    await this.humanGoto(`${this.baseUrl}/my/reservations/upcoming`);
    await this.page.waitForLoadState('networkidle', { timeout: 30000 });
    await humanDelay();
    
    // Find the reservation
    const resCard = await this.page.locator(
      `[data-test="reservation-card"]:has-text("${confirmationNumber}"), [class*="reservation"]:has-text("${confirmationNumber}")`
    ).first();
    
    if (!await resCard.count()) {
      return { success: false, error: 'Reservation not found' };
    }

    // Click cancel button
    const cancelBtn = await resCard.locator('button:has-text("Cancel"), a:has-text("Cancel")').first();
    if (await cancelBtn.count()) {
      await humanDelay();
      await cancelBtn.click();
      await humanDelay();
      
      // Confirm cancellation
      const confirmCancel = await this.page.locator(
        'button:has-text("Confirm"), button:has-text("Yes")'
      ).first();
      
      if (await confirmCancel.count()) {
        await confirmCancel.click();
        await this.page.waitForLoadState('networkidle', { timeout: 30000 });
        
        return { success: true };
      }
    }

    return { success: false, error: 'Could not cancel reservation' };
  }

  /**
   * Test connection - just load the homepage to verify no bot blocking
   */
  async testConnection() {
    console.log('Testing OpenTable connection with stealth mode...');
    const startTime = Date.now();
    
    try {
      await this.humanGoto(this.baseUrl);
      // humanGoto already handles networkidle with timeout fallback
      
      const elapsed = Date.now() - startTime;
      
      // Check for Cloudflare challenge or bot detection
      const pageContent = await this.page.content();
      const isBlocked = pageContent.includes('challenge-platform') || 
                        pageContent.includes('cf-browser-verification') ||
                        pageContent.includes('Just a moment') ||
                        pageContent.includes('Checking your browser');
      
      const title = await this.page.title();
      const url = this.page.url();
      
      if (isBlocked) {
        return { 
          success: false, 
          error: 'Bot detection triggered',
          elapsed,
          title,
          url
        };
      }
      
      // Look for OpenTable-specific elements
      const hasContent = await this.page.locator('input[placeholder*="Location"], input[data-test*="search"], [class*="SearchBar"]').count() > 0;
      
      return {
        success: true,
        elapsed,
        title,
        url,
        hasContent
      };
    } catch (e) {
      return {
        success: false,
        error: e.message,
        elapsed: Date.now() - startTime
      };
    }
  }
}

export default OpenTableClient;

// CLI usage
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [,, command, ...args] = process.argv;
  
  (async () => {
    const client = new OpenTableClient();
    await client.init();

    try {
      switch (command) {
        case 'test': {
          const result = await client.testConnection();
          console.log(JSON.stringify(result, null, 2));
          break;
        }
        case 'login': {
          const result = await client.login();
          console.log(JSON.stringify(result, null, 2));
          break;
        }
        case 'search': {
          const [location, date, time, partySize, cuisine] = args;
          const results = await client.searchRestaurants(location, date, time, partySize || 2, cuisine);
          console.log(JSON.stringify(results, null, 2));
          break;
        }
        case 'availability': {
          const [restaurantId, date, time, partySize] = args;
          const slots = await client.getAvailability(restaurantId, date, time, partySize || 2);
          console.log(JSON.stringify(slots, null, 2));
          break;
        }
        case 'book': {
          const [restaurantId, date, time, partySize] = args;
          const result = await client.makeReservation(restaurantId, date, time, partySize || 2);
          console.log(JSON.stringify(result, null, 2));
          break;
        }
        case 'reservations': {
          const reservations = await client.getMyReservations();
          console.log(JSON.stringify(reservations, null, 2));
          break;
        }
        case 'cancel': {
          const [confNumber] = args;
          const result = await client.cancelReservation(confNumber);
          console.log(JSON.stringify(result, null, 2));
          break;
        }
        default:
          console.log('Usage: node opentable-client.js <command> [args]');
          console.log('Commands: test, login, search, availability, book, reservations, cancel');
      }
    } finally {
      await client.close();
    }
  })().catch(console.error);
}
