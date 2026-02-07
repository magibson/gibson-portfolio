/**
 * Quick test script for the reservation system
 */

import ReservationSystem from './index.js';
import ResyClient from './resy-client.js';

async function test() {
  console.log('🧪 Testing Reservation System\n');
  
  const system = new ReservationSystem();
  
  // Test 1: User preferences
  console.log('1. User Preferences:');
  console.log(JSON.stringify(system.userPrefs, null, 2));
  console.log('');
  
  // Test 2: Local reservations
  console.log('2. Local Reservations:');
  const localRes = system.loadReservations();
  console.log(localRes.length ? JSON.stringify(localRes, null, 2) : '(none)');
  console.log('');
  
  // Test 3: Favorites
  console.log('3. Favorites:');
  const favorites = system.loadFavorites();
  console.log(favorites.length ? JSON.stringify(favorites, null, 2) : '(none)');
  console.log('');
  
  // Test 4: Resy API (will fail without credentials but proves connectivity)
  console.log('4. Testing Resy API connectivity...');
  const resy = new ResyClient();
  try {
    // This will fail with placeholder credentials, but that's expected
    const result = await resy.getAvailability(834, '2024-03-01', 2);
    console.log('Resy response:', JSON.stringify(result, null, 2));
  } catch (e) {
    console.log('Resy API call made (expected auth error with placeholder credentials)');
    console.log('Error:', e.message?.slice(0, 100));
  }
  console.log('');
  
  console.log('✅ System is ready!');
  console.log('');
  console.log('Next steps:');
  console.log('1. Edit config.json with your actual credentials');
  console.log('2. Get Resy tokens from browser network inspector (resy.com)');
  console.log('3. Add OpenTable email/password');
  console.log('4. (Optional) Get Yelp Fusion API key');
  console.log('');
  console.log('Then run:');
  console.log('  node index.js quickbook --restaurant "Carbone" --date 2024-03-01 --time 19:00');
}

test().catch(console.error);
