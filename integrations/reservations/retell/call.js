#!/usr/bin/env node
/**
 * Make a restaurant reservation call via Retell AI
 * 
 * Usage:
 *   node call.js --restaurant "Carbone" --phone "+12125551234" --date "2026-02-01" --time "19:00" --party 2
 *   node call.js --phone "+12125551234" --date "Saturday" --time "7pm" --party 2 --notes "outdoor seating"
 */

import RetellClient from './client.js';
import { parseArgs } from 'util';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '.env') });

function formatDate(dateStr) {
  // Handle relative dates
  const today = new Date();
  const lower = dateStr.toLowerCase();
  
  if (lower === 'today') {
    return today.toISOString().split('T')[0];
  }
  if (lower === 'tomorrow') {
    today.setDate(today.getDate() + 1);
    return today.toISOString().split('T')[0];
  }
  
  // Handle day names
  const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  const dayIndex = days.indexOf(lower);
  if (dayIndex !== -1) {
    const currentDay = today.getDay();
    let daysUntil = dayIndex - currentDay;
    if (daysUntil <= 0) daysUntil += 7;
    today.setDate(today.getDate() + daysUntil);
    return today.toISOString().split('T')[0];
  }
  
  // Assume it's already a date string
  return dateStr;
}

function formatTime(timeStr) {
  // Handle common formats
  const lower = timeStr.toLowerCase().replace(/\s/g, '');
  
  // Match patterns like "7pm", "7:30pm", "19:00"
  const match12 = lower.match(/^(\d{1,2})(?::(\d{2}))?(am|pm)$/);
  if (match12) {
    let hours = parseInt(match12[1]);
    const minutes = match12[2] || '00';
    const period = match12[3];
    
    if (period === 'pm' && hours !== 12) hours += 12;
    if (period === 'am' && hours === 12) hours = 0;
    
    return `${hours.toString().padStart(2, '0')}:${minutes}`;
  }
  
  // Assume 24h format
  return timeStr;
}

async function main() {
  const { values } = parseArgs({
    options: {
      restaurant: { type: 'string', short: 'r' },
      phone: { type: 'string', short: 'p' },
      date: { type: 'string', short: 'd' },
      time: { type: 'string', short: 't' },
      party: { type: 'string', short: 'n', default: '2' },
      notes: { type: 'string' },
      wait: { type: 'boolean', default: true },
      help: { type: 'boolean', short: 'h' },
    },
  });

  if (values.help) {
    console.log(`
Restaurant Reservation Call

Usage:
  node call.js --phone <number> --date <date> --time <time> [options]

Required:
  --phone, -p     Restaurant phone number (e.g., +12125551234)
  --date, -d      Reservation date (e.g., "2026-02-01", "Saturday", "tomorrow")
  --time, -t      Reservation time (e.g., "19:00", "7pm", "7:30 PM")

Options:
  --restaurant, -r  Restaurant name (for logging)
  --party, -n       Party size (default: 2)
  --notes           Special requests (e.g., "outdoor seating", "birthday")
  --no-wait         Don't wait for call to complete
  --help, -h        Show this help

Examples:
  node call.js -p "+12125551234" -d "Saturday" -t "7pm" -n 4
  node call.js --phone "+12125551234" --date "2026-02-15" --time "19:30" --party 2 --notes "anniversary dinner"
`);
    return;
  }

  // Validate required args
  if (!values.phone) {
    console.error('❌ --phone is required');
    process.exit(1);
  }
  if (!values.date) {
    console.error('❌ --date is required');
    process.exit(1);
  }
  if (!values.time) {
    console.error('❌ --time is required');
    process.exit(1);
  }

  // Format date and time
  const formattedDate = formatDate(values.date);
  const formattedTime = formatTime(values.time);

  // Build variables for the agent
  const variables = {
    name: process.env.RESERVATION_NAME || 'Matt Gibson',
    callback_phone: process.env.CALLBACK_PHONE || '',
    date: formattedDate,
    time: formattedTime,
    party_size: values.party,
    special_requests: values.notes || '',
  };

  console.log('📞 Making reservation call...');
  console.log(`   Restaurant: ${values.restaurant || 'Unknown'}`);
  console.log(`   Phone: ${values.phone}`);
  console.log(`   Date: ${formattedDate}`);
  console.log(`   Time: ${formattedTime}`);
  console.log(`   Party: ${values.party}`);
  if (values.notes) {
    console.log(`   Notes: ${values.notes}`);
  }
  console.log('');

  const client = new RetellClient();

  try {
    const call = await client.makeCall(values.phone, variables);
    
    console.log(`Call ID: ${call.call_id}`);
    console.log(`Status: ${call.call_status}`);

    if (values.wait) {
      console.log('\n⏳ Waiting for call to complete...\n');
      
      const result = await client.waitForCall(call.call_id);
      
      if (result.success) {
        console.log('✅ Call completed');
        console.log(`   Duration: ${Math.round(result.duration / 1000)}s`);
        console.log(`   End reason: ${result.endReason}`);
        
        if (result.analysis) {
          console.log('\n📋 Results:');
          if (result.analysis.reservation_confirmed) {
            console.log('   ✅ Reservation CONFIRMED');
            console.log(`   Date: ${result.analysis.confirmed_date}`);
            console.log(`   Time: ${result.analysis.confirmed_time}`);
            console.log(`   Party: ${result.analysis.confirmed_party_size}`);
          } else {
            console.log('   ❌ Reservation not confirmed');
          }
          if (result.analysis.notes) {
            console.log(`   Notes: ${result.analysis.notes}`);
          }
        }
        
        if (result.transcript) {
          console.log('\n📝 Transcript:');
          console.log(result.transcript);
        }
      } else {
        console.log('❌ Call failed');
        console.log(`   Status: ${result.status}`);
        console.log(`   Error: ${result.error}`);
      }
    }
    
    return call;
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

main();
