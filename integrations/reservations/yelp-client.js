/**
 * Yelp Reservations Client
 * 
 * Uses Yelp Fusion API for search and business info.
 * Note: Yelp's reservation system is typically powered by Yelp Reservations
 * or partner systems. Direct booking may require browser automation.
 * 
 * API Key: https://www.yelp.com/developers/v3/manage_app
 */

import fetch from 'node-fetch';
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

class YelpClient {
  constructor(configPath = path.join(__dirname, 'config.json')) {
    this.baseUrl = 'https://api.yelp.com/v3';
    this.webUrl = 'https://www.yelp.com';
    this.configPath = configPath;
    this.config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    this.apiKey = this.config.credentials?.yelp?.api_key || '';
    this.browser = null;
    this.page = null;
  }

  get headers() {
    return {
      'Authorization': `Bearer ${this.apiKey}`,
      'Accept': 'application/json'
    };
  }

  async initBrowser() {
    if (!this.browser) {
      this.browser = await chromium.launch({ headless: true });
      const context = await this.browser.newContext({
        userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
      });
      this.page = await context.newPage();
    }
  }

  async closeBrowser() {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
      this.page = null;
    }
  }

  /**
   * Search for restaurants (API)
   */
  async searchRestaurants(location, term = 'restaurants', options = {}) {
    const params = new URLSearchParams({
      location,
      term,
      categories: 'restaurants',
      limit: options.limit || 20,
      sort_by: options.sortBy || 'best_match'
    });

    if (options.openAt) {
      params.set('open_at', Math.floor(new Date(options.openAt).getTime() / 1000));
    }
    if (options.price) {
      params.set('price', options.price); // 1, 2, 3, 4 ($ to $$$$)
    }

    const response = await fetch(`${this.baseUrl}/businesses/search?${params}`, {
      headers: this.headers
    });
    
    const data = await response.json();
    
    return data.businesses?.map(b => ({
      id: b.id,
      name: b.name,
      rating: b.rating,
      reviewCount: b.review_count,
      price: b.price,
      categories: b.categories?.map(c => c.title),
      address: b.location?.display_address?.join(', '),
      phone: b.display_phone,
      url: b.url,
      coordinates: b.coordinates,
      hasReservations: b.transactions?.includes('restaurant_reservation')
    })) || [];
  }

  /**
   * Get business details (API)
   */
  async getBusinessDetails(businessId) {
    const response = await fetch(`${this.baseUrl}/businesses/${businessId}`, {
      headers: this.headers
    });
    return response.json();
  }

  /**
   * Check availability via browser (Yelp Reservations)
   */
  async checkAvailability(businessUrl, date, time, partySize = 2) {
    await this.initBrowser();
    
    // Add reservation params to URL
    const url = new URL(businessUrl);
    // Navigate to the business page
    await this.page.goto(url.toString());
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForTimeout(2000);

    // Look for Yelp Reservations widget
    const reservationWidget = await this.page.locator(
      '[data-testid="reservation-component"], [class*="reservation"], #reservation'
    ).first();

    if (!await reservationWidget.count()) {
      return { available: false, error: 'No reservation widget found - may use external booking' };
    }

    // Try to set date/time/party
    const dateInput = await this.page.locator('input[type="date"], [class*="date-picker"]').first();
    if (await dateInput.count()) {
      await dateInput.fill(date);
    }

    const timeSelect = await this.page.locator('select[class*="time"], [class*="time-select"]').first();
    if (await timeSelect.count()) {
      await timeSelect.selectOption({ label: time });
    }

    const partySelect = await this.page.locator('select[class*="party"], select[class*="covers"]').first();
    if (await partySelect.count()) {
      await partySelect.selectOption(partySize.toString());
    }

    // Click find times
    const findButton = await this.page.locator('button:has-text("Find"), button:has-text("Search")').first();
    if (await findButton.count()) {
      await findButton.click();
      await this.page.waitForTimeout(2000);
    }

    // Extract available times
    const slots = await this.page.evaluate(() => {
      const times = [];
      document.querySelectorAll('[class*="time-slot"], button[class*="time"]').forEach(el => {
        const text = el.textContent?.trim();
        if (text && /\d{1,2}:\d{2}/.test(text)) {
          times.push({
            time: text,
            available: !el.disabled
          });
        }
      });
      return times;
    });

    return { available: slots.length > 0, slots };
  }

  /**
   * Make reservation via browser
   */
  async makeReservation(businessUrl, date, time, partySize = 2) {
    const availability = await this.checkAvailability(businessUrl, date, time, partySize);
    
    if (!availability.available) {
      return { success: false, error: 'No availability', details: availability };
    }

    // Click the time slot
    const timeSlot = await this.page.locator(
      `button:has-text("${time}"), [class*="time-slot"]:has-text("${time}")`
    ).first();

    if (await timeSlot.count()) {
      await timeSlot.click();
      await this.page.waitForTimeout(2000);

      // Fill guest info
      const userPrefs = this.config.user_preferences;
      
      const nameInput = await this.page.locator('input[name="name"], input[name="first_name"]').first();
      if (await nameInput.count() && userPrefs.name) {
        await nameInput.fill(userPrefs.name);
      }

      const emailInput = await this.page.locator('input[name="email"]').first();
      if (await emailInput.count() && userPrefs.email) {
        await emailInput.fill(userPrefs.email);
      }

      const phoneInput = await this.page.locator('input[name="phone"], input[type="tel"]').first();
      if (await phoneInput.count() && userPrefs.phone) {
        await phoneInput.fill(userPrefs.phone);
      }

      // Submit
      const submitBtn = await this.page.locator(
        'button[type="submit"], button:has-text("Complete"), button:has-text("Reserve")'
      ).first();

      if (await submitBtn.count()) {
        await submitBtn.click();
        await this.page.waitForLoadState('networkidle');
        await this.page.waitForTimeout(3000);

        // Check for success
        const success = await this.page.evaluate(() => {
          return document.body.textContent?.includes('confirmed') ||
                 document.body.textContent?.includes('Reservation') ||
                 document.querySelector('[class*="success"], [class*="confirmation"]');
        });

        return { success: !!success, url: this.page.url() };
      }
    }

    return { success: false, error: 'Could not complete booking' };
  }
}

export default YelpClient;

// CLI usage
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [,, command, ...args] = process.argv;
  
  (async () => {
    const client = new YelpClient();

    try {
      switch (command) {
        case 'search': {
          const [location, term] = args;
          const results = await client.searchRestaurants(location || 'New York', term);
          console.log(JSON.stringify(results, null, 2));
          break;
        }
        case 'details': {
          const [businessId] = args;
          const details = await client.getBusinessDetails(businessId);
          console.log(JSON.stringify(details, null, 2));
          break;
        }
        case 'availability': {
          const [url, date, time, partySize] = args;
          const result = await client.checkAvailability(url, date, time, partySize || 2);
          console.log(JSON.stringify(result, null, 2));
          break;
        }
        default:
          console.log('Usage: node yelp-client.js <command> [args]');
          console.log('Commands: search, details, availability');
      }
    } finally {
      await client.closeBrowser();
    }
  })().catch(console.error);
}
