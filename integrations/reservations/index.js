/**
 * Unified Dinner Reservation System
 * 
 * Combines Resy API, OpenTable browser automation, and Yelp for
 * comprehensive restaurant search and booking capabilities.
 * 
 * Primary flow: Resy API (fast, reliable) → OpenTable (browser) → Yelp (search)
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import ResyClient from './resy-client.js';
import OpenTableClient from './opentable-client.js';
import YelpClient from './yelp-client.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

class ReservationSystem {
  constructor(configPath = path.join(__dirname, 'config.json')) {
    this.configPath = configPath;
    this.config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    
    this.resy = new ResyClient(configPath);
    this.opentable = new OpenTableClient(configPath);
    this.yelp = new YelpClient(configPath);
    
    this.reservationsFile = path.join(__dirname, 'my-reservations.json');
    this.favoritesFile = path.join(__dirname, 'favorites.json');
  }

  /**
   * Get user preferences
   */
  get userPrefs() {
    return this.config.user_preferences;
  }

  /**
   * Update user preferences
   */
  updatePreferences(prefs) {
    this.config.user_preferences = { ...this.config.user_preferences, ...prefs };
    fs.writeFileSync(this.configPath, JSON.stringify(this.config, null, 2));
    return this.config.user_preferences;
  }

  /**
   * Search restaurants across platforms
   */
  async searchRestaurants(options) {
    const {
      location = 'New York',
      cuisine = '',
      date,
      time = '19:00',
      partySize = this.userPrefs.default_party_size || 2,
      platforms = ['resy', 'opentable', 'yelp']
    } = options;

    const results = {
      resy: [],
      opentable: [],
      yelp: [],
      combined: []
    };

    const errors = [];

    // Search Resy
    if (platforms.includes('resy')) {
      try {
        const resyResults = await this.resy.searchRestaurants(cuisine || location, location, partySize);
        results.resy = resyResults.search?.hits?.map(h => ({
          source: 'resy',
          id: h.id?.resy,
          name: h.name,
          cuisine: h.cuisine?.join(', '),
          neighborhood: h.region?.name,
          rating: h.rating,
          price: h.price_range
        })) || [];
      } catch (e) {
        errors.push({ platform: 'resy', error: e.message });
      }
    }

    // Search OpenTable (requires browser)
    if (platforms.includes('opentable') && date) {
      try {
        await this.opentable.init();
        const otResults = await this.opentable.searchRestaurants(
          location, date, time, partySize, cuisine
        );
        results.opentable = otResults.map(r => ({
          source: 'opentable',
          ...r
        }));
        await this.opentable.close();
      } catch (e) {
        errors.push({ platform: 'opentable', error: e.message });
        await this.opentable.close();
      }
    }

    // Search Yelp
    if (platforms.includes('yelp')) {
      try {
        const yelpResults = await this.yelp.searchRestaurants(location, cuisine || 'restaurants');
        results.yelp = yelpResults.map(r => ({
          source: 'yelp',
          ...r
        }));
      } catch (e) {
        errors.push({ platform: 'yelp', error: e.message });
      }
    }

    // Combine and dedupe by name
    const seen = new Set();
    results.combined = [...results.resy, ...results.opentable, ...results.yelp]
      .filter(r => {
        const key = r.name?.toLowerCase().replace(/[^a-z0-9]/g, '');
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });

    return { results, errors };
  }

  /**
   * Check availability at a specific restaurant
   */
  async checkAvailability(options) {
    const {
      restaurant,      // Can be { platform, id } or restaurant name
      date,            // YYYY-MM-DD
      time = '19:00',  // HH:MM
      partySize = this.userPrefs.default_party_size || 2
    } = options;

    // If platform specified, use that
    if (restaurant.platform === 'resy' && restaurant.id) {
      const slots = await this.resy.getAvailability(restaurant.id, date, partySize);
      return {
        platform: 'resy',
        restaurant: restaurant.name || restaurant.id,
        date,
        partySize,
        slots: slots.map(s => ({
          time: s.time,
          type: s.type,
          available: true,
          token: s.token
        }))
      };
    }

    if (restaurant.platform === 'opentable' && restaurant.id) {
      await this.opentable.init();
      const slots = await this.opentable.getAvailability(restaurant.id, date, time, partySize);
      await this.opentable.close();
      return {
        platform: 'opentable',
        restaurant: restaurant.name || restaurant.id,
        date,
        partySize,
        slots
      };
    }

    return { error: 'Please specify platform and restaurant ID' };
  }

  /**
   * Make a reservation
   */
  async makeReservation(options) {
    const {
      platform,
      restaurantId,
      restaurantName,
      date,           // YYYY-MM-DD
      time,           // HH:MM
      partySize = this.userPrefs.default_party_size || 2,
      name = this.userPrefs.name,
      phone = this.userPrefs.phone,
      email = this.userPrefs.email
    } = options;

    let result;

    if (platform === 'resy') {
      // Use Resy API
      result = await this.resy.bookSlot(restaurantId, date, time, partySize);
      
      if (result.success) {
        this.saveReservation({
          platform: 'resy',
          restaurant: restaurantName || restaurantId,
          date,
          time,
          partySize,
          confirmation: result.confirmation,
          bookedAt: new Date().toISOString()
        });
      }
    } else if (platform === 'opentable') {
      // Use OpenTable browser automation
      await this.opentable.init();
      
      // Login if not already
      if (!fs.existsSync(path.join(__dirname, '.opentable-cookies.json'))) {
        await this.opentable.login();
      }
      
      result = await this.opentable.makeReservation(restaurantId, date, time, partySize);
      await this.opentable.close();
      
      if (result.success) {
        this.saveReservation({
          platform: 'opentable',
          restaurant: restaurantName || restaurantId,
          date,
          time,
          partySize,
          confirmation: result.confirmation,
          bookedAt: new Date().toISOString()
        });
      }
    } else {
      return { success: false, error: 'Unknown platform. Use "resy" or "opentable"' };
    }

    return result;
  }

  /**
   * Cancel a reservation
   */
  async cancelReservation(options) {
    const { platform, confirmationId } = options;

    if (platform === 'resy') {
      const result = await this.resy.cancelReservation(confirmationId);
      if (result.success !== false) {
        this.removeReservation(confirmationId);
      }
      return result;
    }

    if (platform === 'opentable') {
      await this.opentable.init();
      const result = await this.opentable.cancelReservation(confirmationId);
      await this.opentable.close();
      if (result.success) {
        this.removeReservation(confirmationId);
      }
      return result;
    }

    return { error: 'Unknown platform' };
  }

  /**
   * Get all reservations (from platforms + local cache)
   */
  async getMyReservations(options = {}) {
    const { fetchRemote = false } = options;
    
    const reservations = {
      local: this.loadReservations(),
      resy: [],
      opentable: []
    };

    if (fetchRemote) {
      try {
        const resyRes = await this.resy.getMyReservations();
        reservations.resy = resyRes.reservations || [];
      } catch (e) {
        reservations.resyError = e.message;
      }

      try {
        await this.opentable.init();
        reservations.opentable = await this.opentable.getMyReservations();
        await this.opentable.close();
      } catch (e) {
        reservations.opentableError = e.message;
        await this.opentable.close();
      }
    }

    return reservations;
  }

  /**
   * Save a reservation to local storage
   */
  saveReservation(reservation) {
    const reservations = this.loadReservations();
    reservations.push(reservation);
    fs.writeFileSync(this.reservationsFile, JSON.stringify(reservations, null, 2));
    return reservation;
  }

  /**
   * Load reservations from local storage
   */
  loadReservations() {
    if (!fs.existsSync(this.reservationsFile)) {
      return [];
    }
    return JSON.parse(fs.readFileSync(this.reservationsFile, 'utf8'));
  }

  /**
   * Remove a reservation from local storage
   */
  removeReservation(confirmationId) {
    const reservations = this.loadReservations();
    const filtered = reservations.filter(r => r.confirmation !== confirmationId);
    fs.writeFileSync(this.reservationsFile, JSON.stringify(filtered, null, 2));
  }

  /**
   * Add a favorite restaurant
   */
  addFavorite(restaurant) {
    const favorites = this.loadFavorites();
    if (!favorites.find(f => f.id === restaurant.id && f.platform === restaurant.platform)) {
      favorites.push({
        ...restaurant,
        addedAt: new Date().toISOString()
      });
      fs.writeFileSync(this.favoritesFile, JSON.stringify(favorites, null, 2));
    }
    return favorites;
  }

  /**
   * Load favorites
   */
  loadFavorites() {
    if (!fs.existsSync(this.favoritesFile)) {
      return [];
    }
    return JSON.parse(fs.readFileSync(this.favoritesFile, 'utf8'));
  }

  /**
   * Quick book - finds availability and books in one call
   */
  async quickBook(options) {
    const {
      restaurantName,
      location = 'New York',
      date,
      preferredTime = '19:00',
      partySize = this.userPrefs.default_party_size || 2,
      platform = 'resy'  // Prefer Resy for API booking
    } = options;

    console.log(`🔍 Searching for ${restaurantName}...`);

    // Search for the restaurant
    const searchResults = await this.searchRestaurants({
      location,
      cuisine: restaurantName,
      date,
      time: preferredTime,
      partySize,
      platforms: [platform]
    });

    const restaurants = searchResults.results[platform];
    if (!restaurants.length) {
      return { success: false, error: `No restaurants found matching "${restaurantName}"` };
    }

    // Find best match
    const match = restaurants.find(r => 
      r.name?.toLowerCase().includes(restaurantName.toLowerCase())
    ) || restaurants[0];

    console.log(`📍 Found: ${match.name}`);

    // Check availability
    const availability = await this.checkAvailability({
      restaurant: { platform, id: match.id, name: match.name },
      date,
      time: preferredTime,
      partySize
    });

    if (!availability.slots?.length) {
      return { success: false, error: 'No availability', restaurant: match };
    }

    console.log(`🕐 Available times: ${availability.slots.map(s => s.time).join(', ')}`);

    // Find closest time to preferred
    const preferredMinutes = parseInt(preferredTime.split(':')[0]) * 60 + parseInt(preferredTime.split(':')[1]);
    const bestSlot = availability.slots.reduce((best, slot) => {
      const slotTime = slot.time?.match(/(\d{1,2}):(\d{2})/);
      if (!slotTime) return best;
      
      const slotMinutes = parseInt(slotTime[1]) * 60 + parseInt(slotTime[2]);
      const diff = Math.abs(slotMinutes - preferredMinutes);
      
      if (!best || diff < best.diff) {
        return { slot, diff };
      }
      return best;
    }, null)?.slot;

    if (!bestSlot) {
      return { success: false, error: 'Could not determine best time slot' };
    }

    const bookTime = bestSlot.time?.match(/(\d{1,2}):(\d{2})/)?.[0] || preferredTime;
    console.log(`📝 Booking for ${bookTime}...`);

    // Make the reservation
    const result = await this.makeReservation({
      platform,
      restaurantId: match.id,
      restaurantName: match.name,
      date,
      time: bookTime,
      partySize
    });

    return {
      ...result,
      restaurant: match,
      date,
      time: bookTime,
      partySize
    };
  }
}

export default ReservationSystem;

// CLI usage
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const system = new ReservationSystem();
  const [,, command, ...args] = process.argv;

  const parseArgs = (args) => {
    const opts = {};
    for (let i = 0; i < args.length; i += 2) {
      const key = args[i].replace('--', '');
      opts[key] = args[i + 1];
    }
    return opts;
  };

  const commands = {
    async search() {
      const opts = parseArgs(args);
      const results = await system.searchRestaurants(opts);
      console.log(JSON.stringify(results, null, 2));
    },
    
    async availability() {
      const opts = parseArgs(args);
      const result = await system.checkAvailability({
        restaurant: { platform: opts.platform, id: opts.id },
        date: opts.date,
        time: opts.time,
        partySize: parseInt(opts.partySize || '2')
      });
      console.log(JSON.stringify(result, null, 2));
    },
    
    async book() {
      const opts = parseArgs(args);
      const result = await system.makeReservation({
        platform: opts.platform,
        restaurantId: opts.id,
        restaurantName: opts.name,
        date: opts.date,
        time: opts.time,
        partySize: parseInt(opts.partySize || '2')
      });
      console.log(JSON.stringify(result, null, 2));
    },
    
    async quickbook() {
      const opts = parseArgs(args);
      const result = await system.quickBook({
        restaurantName: opts.restaurant,
        location: opts.location,
        date: opts.date,
        preferredTime: opts.time,
        partySize: parseInt(opts.partySize || '2'),
        platform: opts.platform
      });
      console.log(JSON.stringify(result, null, 2));
    },
    
    async cancel() {
      const opts = parseArgs(args);
      const result = await system.cancelReservation({
        platform: opts.platform,
        confirmationId: opts.confirmation
      });
      console.log(JSON.stringify(result, null, 2));
    },
    
    async reservations() {
      const opts = parseArgs(args);
      const result = await system.getMyReservations({
        fetchRemote: opts.remote === 'true'
      });
      console.log(JSON.stringify(result, null, 2));
    },
    
    async prefs() {
      console.log(JSON.stringify(system.userPrefs, null, 2));
    },
    
    async favorites() {
      console.log(JSON.stringify(system.loadFavorites(), null, 2));
    }
  };

  if (commands[command]) {
    commands[command]().catch(e => {
      console.error('Error:', e.message);
      process.exit(1);
    });
  } else {
    console.log(`
Reservation System CLI

Commands:
  search --location "NYC" --cuisine "Italian" --date 2024-02-15 --time 19:00 --partySize 2
  availability --platform resy --id 12345 --date 2024-02-15 --time 19:00
  book --platform resy --id 12345 --date 2024-02-15 --time 19:00 --partySize 2
  quickbook --restaurant "Carbone" --location "NYC" --date 2024-02-15 --time 19:00
  cancel --platform resy --confirmation abc123
  reservations --remote true
  prefs
  favorites
    `);
  }
}
