#!/usr/bin/env node
/**
 * Jarvis Personal Call - Quick outbound call to Matt
 */

import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '../reservations/retell/.env') });

const RETELL_API_BASE = 'https://api.retellai.com';

async function makeCall(message = "Hey Matt, this is Jarvis. Just testing the call system. Talk to you soon!") {
  const apiKey = process.env.RETELL_API_KEY;
  const fromNumber = process.env.RETELL_PHONE_NUMBER_ID;
  const toNumber = process.env.CALLBACK_PHONE;

  console.log(`📞 Calling ${toNumber} from ${fromNumber}...`);
  console.log(`📝 Message: ${message}`);

  // Create a simple agent for this call
  const llmResponse = await fetch(`${RETELL_API_BASE}/create-retell-llm`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      general_prompt: `You are Jarvis, Matt's AI assistant. You're calling to deliver this message: "${message}". Be friendly, casual, and brief. After delivering the message, ask if there's anything Matt wants you to do. Keep it under 30 seconds. End politely.`,
    }),
  });
  
  const llm = await llmResponse.json();
  console.log('Created LLM:', llm.llm_id);

  // Create agent
  const agentResponse = await fetch(`${RETELL_API_BASE}/create-agent`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      agent_name: 'Jarvis Personal Call',
      voice_id: '11labs-Adrian',
      response_engine: {
        type: 'retell-llm',
        llm_id: llm.llm_id,
      },
      voice_temperature: 0.7,
      voice_speed: 1.0,
      language: 'en-US',
      max_call_duration_ms: 120000,
    }),
  });

  const agent = await agentResponse.json();
  console.log('Created agent:', agent.agent_id);

  // Make the call
  const callResponse = await fetch(`${RETELL_API_BASE}/v2/create-phone-call`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from_number: fromNumber,
      to_number: toNumber,
      agent_id: agent.agent_id,
    }),
  });

  const call = await callResponse.json();
  console.log('📞 Call initiated!');
  console.log('Call ID:', call.call_id);
  
  return call;
}

// Get message from command line or use default
const message = process.argv[2] || "Hey Matt, this is Jarvis. Just a quick test call to make sure this works. Pretty cool, right?";
makeCall(message).catch(console.error);
