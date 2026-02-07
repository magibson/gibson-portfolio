/**
 * Resy API Client
 * 
 * Uses Resy's internal API for searching and booking reservations.
 * 
 * CREDENTIAL SOURCES (in priority order):
 * 1. Environment variables (RESY_API_KEY, RESY_AUTH_TOKEN)
 * 2. .env file in this directory
 * 3. config.json (legacy, not recommended for credentials)
 * 
 * To get credentials:
 * 1. Log into resy.com in Chrome
 * 2. Open DevTools → Network tab
 * 3. Navigate to any restaurant page
 * 4. Find a request to api.resy.com
 * 5. Copy 'authorization' header (part after 'api_key=')
 * 6. Copy 'x-resy-auth-token' header
 * 
 * See SECURITY.md for full documentation.
 */

import fetch from 'node-fetch';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { config as dotenvConfig } from 'dotenv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load .env file if it exists
const envPath = path.join(__dirname, '.env');
if (fs.existsSync(envPath)) {
  dotenvConfig({ path: envPath });
}

class ResyClient {
  constructor(configPath = path.join(__dirname, 'config.json')) {
    this.baseUrl = process.env.RESY_BASE_URL || 'https://api.resy.com';
    this.configPath = configPath;
    
    // Load config for non-credential settings
    this.config = {};
    if (fs.existsSync(configPath)) {
      try {
        this.config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      } catch (e) {
        console.warn('Warning: Could not parse config.json');
      }
    }
    
    // Credentials: prefer env vars over config file
    this.apiKey = process.env.RESY_API_KEY || this.config.credentials?.resy?.api_key || '';
    this.authToken = process.env.RESY_AUTH_TOKEN || this.config.credentials?.resy?.auth_token || '';
    
    // Validate credentials (don't log them!)
    if (!this.apiKey || this.apiKey.includes('PLACEHOLDER')) {
      console.warn('⚠️  RESY_API_KEY not configured. See SECURITY.md for setup instructions.');
    }
    if (!this.authToken || this.authToken.includes('PLACEHOLDER')) {
      console.warn('⚠️  RESY_AUTH_TOKEN not configured. See SECURITY.md for setup instructions.');
    }
  }

  get headers() {
    return {
      'Authorization': `ResyAPI api_key="${this.apiKey}"`,
      'X-Resy-Auth-Token': this.authToken,
      'X-Resy-Universal-Auth': this.authToken,
      'Content-Type': 'application/x-www-form-urlencoded',
      'Origin': 'https://resy.com',
      'Referer': 'https://resy.com/',
      'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    };
  }

  /**
   * Login to Resy and get auth token
   * 
   * NOTE: This method is provided for completeness but manual token extraction
   * is recommended for security (avoids storing password).
   * 
   * @param {string} email - Resy account email
   * @param {string} password - Resy account password
   * @returns {object} Login response with token
   */
  async login(email, password) {
    const userEmail = email || process.env.RESY_EMAIL || this.config.credentials?.resy?.email;
    const userPassword = password || process.env.RESY_PASSWORD || this.config.credentials?.resy?.password;
    
    if (!userEmail || !userPassword) {
      throw new Error('Email and password required for login. See SECURITY.md for setup.');
    }
    
    const response = await fetch(`${this.baseUrl}/3/auth/password`, {
      method: 'POST',
      headers: {
        'Authorization': `ResyAPI api_key="${this.apiKey}"`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        email: userEmail,
        password: userPassword
      })
    });
    
    const data = await response.json();
    if (data.token) {
      this.authToken = data.token;
      
      // Save token to .env file (secure approach)
      const envPath = path.join(__dirname, '.env');
      let envContent = '';
      if (fs.existsSync(envPath)) {
        envContent = fs.readFileSync(envPath, 'utf8');
      }
      
      // Update or add RESY_AUTH_TOKEN
      if (envContent.includes('RESY_AUTH_TOKEN=')) {
        envContent = envContent.replace(/RESY_AUTH_TOKEN=.*/, `RESY_AUTH_TOKEN=${data.token}`);
      } else {
        envContent += `\nRESY_AUTH_TOKEN=${data.token}`;
      }
      
      fs.writeFileSync(envPath, envContent);
      fs.chmodSync(envPath, 0o600); // Restrict permissions
      
      console.log('✅ Resy login successful, token saved to .env');
    } else if (data.message) {
      console.error('❌ Login failed:', data.message);
    }
    return data;
  }

  /**
   * Search for restaurants by location/query
   */
  async searchRestaurants(query, location = 'New York', partySize = 2) {
    const params = new URLSearchParams({
      query: query,
      geo: JSON.stringify({ latitude: 40.7128, longitude: -74.0060 }), // NYC default
      per_page: 20,
      party_size: partySize
    });

    const response = await fetch(`${this.baseUrl}/3/venuesearch/search?${params}`, {
      headers: this.headers
    });
    
    return response.json();
  }

  /**
   * Get venue details by ID
   */
  async getVenue(venueId) {
    const response = await fetch(`${this.baseUrl}/4/venue?id=${venueId}`, {
      headers: this.headers
    });
    return response.json();
  }

  /**
   * Get available dates for a venue
   */
  async getAvailableDates(venueId, partySize = 2, numMonths = 2) {
    const params = new URLSearchParams({
      venue_id: venueId,
      party_size: partySize,
      num_months: numMonths
    });

    const response = await fetch(`${this.baseUrl}/4/venue/calendar?${params}`, {
      headers: this.headers
    });
    
    return response.json();
  }

  /**
   * Get available time slots for a venue on a specific date
   */
  async getAvailability(venueId, date, partySize = 2) {
    const params = new URLSearchParams({
      venue_id: venueId,
      day: date,
      party_size: partySize,
      lat: 0,
      long: 0
    });

    const response = await fetch(`${this.baseUrl}/4/find?${params}`, {
      headers: this.headers
    });
    
    const data = await response.json();
    
    // Extract slots
    if (data.results?.venues?.[0]?.slots) {
      return data.results.venues[0].slots.map(slot => ({
        time: slot.date?.start,
        endTime: slot.date?.end,
        type: slot.config?.type,
        token: slot.config?.token,
        paymentRequired: slot.payment?.is_paid,
        cancellationFee: slot.payment?.cancellation_fee
      }));
    }
    
    return [];
  }

  /**
   * Get booking details (config token) for a specific slot
   */
  async getSlotDetails(configToken, date, partySize = 2) {
    const params = new URLSearchParams({
      config_id: configToken,
      day: date,
      party_size: partySize
    });

    const response = await fetch(`${this.baseUrl}/3/details?${params}`, {
      headers: this.headers
    });
    
    return response.json();
  }

  /**
   * Make a reservation
   */
  async makeReservation(bookToken, partySize = 2, structPaymentMethod = null) {
    const body = new URLSearchParams({
      book_token: bookToken,
      party_size: partySize,
      source_id: 'resy.com-venue-details'
    });

    if (structPaymentMethod) {
      body.append('struct_payment_method', JSON.stringify(structPaymentMethod));
    }

    const response = await fetch(`${this.baseUrl}/3/book`, {
      method: 'POST',
      headers: this.headers,
      body: body
    });
    
    return response.json();
  }

  /**
   * Full booking flow: get slot details then book
   */
  async bookSlot(venueId, date, time, partySize = 2) {
    // Get available slots
    const slots = await this.getAvailability(venueId, date, partySize);
    
    // Find matching slot
    const targetSlot = slots.find(s => s.time?.includes(time));
    if (!targetSlot) {
      return { success: false, error: 'No slot available at requested time', availableSlots: slots };
    }

    // Get booking details
    const details = await this.getSlotDetails(targetSlot.token, date, partySize);
    if (!details.book_token) {
      return { success: false, error: 'Could not get booking token', details };
    }

    // Make the reservation
    const result = await this.makeReservation(details.book_token.value, partySize);
    
    return {
      success: !!result.resy_token,
      confirmation: result.resy_token,
      details: result
    };
  }

  /**
   * Get user's reservations
   */
  async getMyReservations() {
    const response = await fetch(`${this.baseUrl}/3/user/reservations?limit=20`, {
      headers: this.headers
    });
    
    return response.json();
  }

  /**
   * Cancel a reservation
   */
  async cancelReservation(resyToken) {
    const body = new URLSearchParams({
      resy_token: resyToken
    });

    const response = await fetch(`${this.baseUrl}/3/cancel`, {
      method: 'POST',
      headers: this.headers,
      body: body
    });
    
    return response.json();
  }
}

export default ResyClient;

// CLI usage
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const client = new ResyClient();
  const [,, command, ...args] = process.argv;

  const commands = {
    async search() {
      const [query, location, partySize] = args;
      const results = await client.searchRestaurants(query || 'Italian', location, partySize);
      console.log(JSON.stringify(results, null, 2));
    },
    async availability() {
      const [venueId, date, partySize] = args;
      const slots = await client.getAvailability(venueId, date, partySize || 2);
      console.log(JSON.stringify(slots, null, 2));
    },
    async book() {
      const [venueId, date, time, partySize] = args;
      const result = await client.bookSlot(venueId, date, time, partySize || 2);
      console.log(JSON.stringify(result, null, 2));
    },
    async reservations() {
      const reservations = await client.getMyReservations();
      console.log(JSON.stringify(reservations, null, 2));
    },
    async cancel() {
      const [resyToken] = args;
      const result = await client.cancelReservation(resyToken);
      console.log(JSON.stringify(result, null, 2));
    },
    async login() {
      const result = await client.login();
      console.log(JSON.stringify(result, null, 2));
    }
  };

  if (commands[command]) {
    commands[command]().catch(console.error);
  } else {
    console.log('Usage: node resy-client.js <command> [args]');
    console.log('Commands: search, availability, book, reservations, cancel, login');
  }
}
