/**
 * Simple Booking Interface for Clawdbot
 * 
 * Usage:
 *   node book.js resy search "Italian" 2
 *   node book.js resy availability 1505 2024-02-15 2
 *   node book.js resy book 1505 2024-02-15 19:00 2
 *   node book.js resy reservations
 *   node book.js resy cancel <resy_token>
 *   node book.js status
 * 
 * For OpenTable, use Chrome relay via browser tool.
 */

import ResyClient from './resy-client.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Check if credentials are configured
function checkCredentials() {
  const envPath = path.join(__dirname, '.env');
  const hasEnv = fs.existsSync(envPath);
  const hasApiKey = !!process.env.RESY_API_KEY;
  const hasToken = !!process.env.RESY_AUTH_TOKEN;
  
  return {
    configured: hasEnv && (hasApiKey || hasToken),
    envFile: hasEnv,
    apiKey: hasApiKey,
    authToken: hasToken
  };
}

// Format reservation for display
function formatReservation(res) {
  if (!res) return 'No reservation data';
  return {
    restaurant: res.venue?.name,
    date: res.day,
    time: res.time_slot,
    party_size: res.num_seats,
    confirmation: res.resy_token,
    status: res.reservation?.status
  };
}

// Format search results
function formatSearchResults(results) {
  if (!results?.search?.hits) return [];
  return results.search.hits.map(hit => ({
    name: hit.name,
    venue_id: hit.id?.resy,
    cuisine: hit.cuisine?.join(', '),
    neighborhood: hit.location?.neighborhood,
    price: hit.price_range
  }));
}

// Main CLI
async function main() {
  const [,, platform, command, ...args] = process.argv;

  // Status check
  if (platform === 'status' || !platform) {
    const creds = checkCredentials();
    console.log('Reservation Integration Status:');
    console.log('================================');
    console.log(`Resy credentials configured: ${creds.configured ? '✅ Yes' : '❌ No'}`);
    console.log(`  .env file exists: ${creds.envFile ? '✅' : '❌'}`);
    console.log(`  API Key in env: ${creds.apiKey ? '✅' : '❌'}`);
    console.log(`  Auth Token in env: ${creds.authToken ? '✅' : '❌'}`);
    console.log('');
    if (!creds.configured) {
      console.log('To configure, see: SECURITY.md');
      console.log('Quick start: Copy .env.example to .env and add your tokens');
    }
    return;
  }

  if (platform !== 'resy') {
    console.log('Only "resy" platform is supported via CLI.');
    console.log('For OpenTable, use Chrome relay (browser tool with profile="chrome")');
    return;
  }

  const client = new ResyClient();

  try {
    switch (command) {
      case 'search': {
        const [query, partySize = 2] = args;
        console.log(`Searching for: ${query}`);
        const results = await client.searchRestaurants(query, 'New York', parseInt(partySize));
        const formatted = formatSearchResults(results);
        console.log(JSON.stringify(formatted, null, 2));
        break;
      }

      case 'availability': {
        const [venueId, date, partySize = 2] = args;
        if (!venueId || !date) {
          console.error('Usage: book.js resy availability <venue_id> <date> [party_size]');
          console.error('Example: book.js resy availability 1505 2024-02-15 2');
          return;
        }
        console.log(`Checking availability for venue ${venueId} on ${date}...`);
        const slots = await client.getAvailability(venueId, date, parseInt(partySize));
        if (slots.length === 0) {
          console.log('No available slots found.');
        } else {
          console.log(`Found ${slots.length} available slots:`);
          console.log(JSON.stringify(slots, null, 2));
        }
        break;
      }

      case 'book': {
        const [venueId, date, time, partySize = 2] = args;
        if (!venueId || !date || !time) {
          console.error('Usage: book.js resy book <venue_id> <date> <time> [party_size]');
          console.error('Example: book.js resy book 1505 2024-02-15 19:00 2');
          return;
        }
        console.log(`Booking at venue ${venueId} for ${date} at ${time}...`);
        const result = await client.bookSlot(venueId, date, time, parseInt(partySize));
        if (result.success) {
          console.log('✅ Booking successful!');
          console.log(`Confirmation: ${result.confirmation}`);
        } else {
          console.log('❌ Booking failed:', result.error);
          if (result.availableSlots?.length > 0) {
            console.log('Available times:', result.availableSlots.map(s => s.time).join(', '));
          }
        }
        console.log(JSON.stringify(result, null, 2));
        break;
      }

      case 'reservations': {
        console.log('Fetching your reservations...');
        const reservations = await client.getMyReservations();
        if (reservations.reservations?.length > 0) {
          console.log(`Found ${reservations.reservations.length} reservation(s):`);
          reservations.reservations.forEach((res, i) => {
            console.log(`\n${i + 1}. ${formatReservation(res).restaurant}`);
            console.log(`   Date: ${res.day} at ${res.time_slot}`);
            console.log(`   Party: ${res.num_seats}`);
            console.log(`   Token: ${res.resy_token}`);
          });
        } else {
          console.log('No upcoming reservations found.');
        }
        break;
      }

      case 'cancel': {
        const [resyToken] = args;
        if (!resyToken) {
          console.error('Usage: book.js resy cancel <resy_token>');
          return;
        }
        console.log(`Cancelling reservation ${resyToken}...`);
        const result = await client.cancelReservation(resyToken);
        console.log(JSON.stringify(result, null, 2));
        break;
      }

      case 'venue': {
        const [venueId] = args;
        if (!venueId) {
          console.error('Usage: book.js resy venue <venue_id>');
          return;
        }
        const venue = await client.getVenue(venueId);
        console.log(JSON.stringify(venue, null, 2));
        break;
      }

      default:
        console.log('Resy Booking Commands:');
        console.log('  search <query> [party_size]');
        console.log('  availability <venue_id> <date> [party_size]');
        console.log('  book <venue_id> <date> <time> [party_size]');
        console.log('  reservations');
        console.log('  cancel <resy_token>');
        console.log('  venue <venue_id>');
        console.log('');
        console.log('Examples:');
        console.log('  node book.js resy search "Don Angie" 2');
        console.log('  node book.js resy availability 1505 2024-02-15 2');
        console.log('  node book.js resy book 1505 2024-02-15 19:00 2');
    }
  } catch (error) {
    if (error.message?.includes('401') || error.message?.includes('Unauthorized')) {
      console.error('❌ Authentication failed. Token may be expired.');
      console.error('   Re-extract tokens from Chrome DevTools. See SECURITY.md.');
    } else {
      console.error('Error:', error.message);
    }
  }
}

main().catch(console.error);
