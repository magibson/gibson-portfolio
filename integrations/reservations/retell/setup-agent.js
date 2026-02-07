#!/usr/bin/env node
/**
 * Setup script to create the Retell AI agent for restaurant reservations
 * 
 * Run this once after adding your RETELL_API_KEY to .env
 */

import RetellClient from './client.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function main() {
  console.log('🔧 Setting up Retell AI Restaurant Reservation Agent...\n');

  // Check for API key
  if (!process.env.RETELL_API_KEY) {
    console.error('❌ RETELL_API_KEY not found in .env');
    console.log('\nTo set up:');
    console.log('1. Go to https://www.retellai.com/ and create an account');
    console.log('2. Get your API key from the dashboard');
    console.log('3. Copy .env.example to .env and add your key');
    process.exit(1);
  }

  const client = new RetellClient();

  try {
    // Create the agent
    const agent = await client.createAgent();
    
    // Update .env with agent ID
    const envPath = path.join(__dirname, '.env');
    let envContent = fs.readFileSync(envPath, 'utf8');
    
    if (envContent.includes('RETELL_AGENT_ID=')) {
      envContent = envContent.replace(
        /RETELL_AGENT_ID=.*/,
        `RETELL_AGENT_ID=${agent.agent_id}`
      );
    } else {
      envContent += `\nRETELL_AGENT_ID=${agent.agent_id}`;
    }
    
    fs.writeFileSync(envPath, envContent);
    
    console.log('\n✅ Setup complete!');
    console.log(`   Agent ID: ${agent.agent_id}`);
    console.log('\nNext steps:');
    console.log('1. Go to Retell Dashboard → Phone Numbers');
    console.log('2. Buy a phone number (~$2/month)');
    console.log('3. Copy the Phone Number ID to .env as RETELL_PHONE_NUMBER_ID');
    console.log('4. Add your callback phone and name to .env');
    console.log('\nThen you can make calls with:');
    console.log('  node call.js --restaurant "Restaurant Name" --phone "+1234567890" --date "2026-02-01" --time "19:00" --party 2');
    
  } catch (error) {
    console.error('❌ Setup failed:', error.message);
    process.exit(1);
  }
}

main();
