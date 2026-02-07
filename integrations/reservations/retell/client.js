/**
 * Retell AI Client for Restaurant Reservations
 * 
 * API Reference: https://docs.retellai.com/api-references
 */

import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '.env') });

const RETELL_API_BASE = 'https://api.retellai.com';

class RetellClient {
  constructor(apiKey = process.env.RETELL_API_KEY) {
    if (!apiKey) {
      throw new Error('RETELL_API_KEY is required. Set it in .env file.');
    }
    this.apiKey = apiKey;
    this.agentId = process.env.RETELL_AGENT_ID;
    this.phoneNumberId = process.env.RETELL_PHONE_NUMBER_ID;
  }

  async request(endpoint, options = {}) {
    const url = `${RETELL_API_BASE}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(`Retell API error: ${data.message || JSON.stringify(data)}`);
    }
    
    return data;
  }

  /**
   * Create or update the restaurant reservation agent
   */
  async createAgent(promptTemplate) {
    const prompt = promptTemplate || fs.readFileSync(
      path.join(__dirname, 'agent-prompt.txt'), 
      'utf8'
    );

    const agentConfig = {
      agent_name: 'Restaurant Reservation Agent',
      voice_id: '11labs-Adrian', // Natural male voice
      response_engine: {
        type: 'retell-llm',
        llm_id: null, // Will use default
      },
      llm_websocket_url: null,
      voice_model: 'eleven_turbo_v2',
      voice_temperature: 0.7,
      voice_speed: 1.0,
      responsiveness: 0.8,
      interruption_sensitivity: 0.6,
      enable_backchannel: true,
      backchannel_frequency: 0.7,
      backchannel_words: ['yeah', 'mhm', 'okay', 'right', 'got it'],
      reminder_trigger_ms: 10000,
      reminder_max_count: 2,
      ambient_sound: null,
      language: 'en-US',
      webhook_url: null,
      boosted_keywords: [
        'reservation',
        'table',
        'party',
        'people',
        'tonight',
        'tomorrow',
        'saturday',
        'sunday',
        'outdoor',
        'patio'
      ],
      opt_out_sensitive_data_storage: false,
      pronunciation_dictionary: [],
      normalize_for_speech: true,
      end_call_after_silence_ms: 15000,
      max_call_duration_ms: 300000, // 5 minutes max
      enable_voicemail_detection: true,
      voicemail_message: "Hi, this is a call on behalf of Matt Gibson regarding a restaurant reservation. Please call back at your earliest convenience. Thank you!",
      post_call_analysis_data: [
        {
          name: 'reservation_confirmed',
          type: 'boolean',
          description: 'Whether a reservation was successfully made'
        },
        {
          name: 'confirmed_date',
          type: 'string', 
          description: 'The confirmed date of the reservation'
        },
        {
          name: 'confirmed_time',
          type: 'string',
          description: 'The confirmed time of the reservation'
        },
        {
          name: 'confirmed_party_size',
          type: 'number',
          description: 'The confirmed party size'
        },
        {
          name: 'notes',
          type: 'string',
          description: 'Any additional notes or special instructions'
        }
      ]
    };

    // Create a Retell LLM first
    const llmResponse = await this.request('/create-retell-llm', {
      method: 'POST',
      body: JSON.stringify({
        general_prompt: prompt,
        general_tools: [],
        states: null
      }),
    });

    agentConfig.response_engine.llm_id = llmResponse.llm_id;

    // Now create the agent
    const agentResponse = await this.request('/create-agent', {
      method: 'POST', 
      body: JSON.stringify(agentConfig),
    });

    console.log('✅ Agent created:', agentResponse.agent_id);
    return agentResponse;
  }

  /**
   * Make an outbound call to a restaurant
   */
  async makeCall(toNumber, variables = {}) {
    if (!this.agentId) {
      throw new Error('RETELL_AGENT_ID not set. Run setup-agent.js first.');
    }
    if (!this.phoneNumberId) {
      throw new Error('RETELL_PHONE_NUMBER_ID not set. Buy a number in Retell dashboard.');
    }

    const callConfig = {
      from_number: this.phoneNumberId,
      to_number: toNumber,
      agent_id: this.agentId,
      retell_llm_dynamic_variables: variables,
      metadata: {
        restaurant_phone: toNumber,
        requested_date: variables.date,
        requested_time: variables.time,
        party_size: variables.party_size,
      }
    };

    const response = await this.request('/v2/create-phone-call', {
      method: 'POST',
      body: JSON.stringify(callConfig),
    });

    console.log('📞 Call initiated:', response.call_id);
    return response;
  }

  /**
   * Get call status and details
   */
  async getCall(callId) {
    return this.request(`/v2/get-call/${callId}`);
  }

  /**
   * List recent calls
   */
  async listCalls(limit = 10) {
    return this.request(`/v2/list-calls?limit=${limit}`);
  }

  /**
   * Get call transcript
   */
  async getTranscript(callId) {
    const call = await this.getCall(callId);
    return call.transcript;
  }

  /**
   * Wait for call to complete and return results
   */
  async waitForCall(callId, timeoutMs = 300000) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeoutMs) {
      const call = await this.getCall(callId);
      
      if (call.call_status === 'ended') {
        return {
          success: true,
          status: call.call_status,
          duration: call.call_duration_ms,
          transcript: call.transcript,
          analysis: call.call_analysis,
          endReason: call.end_call_reason,
        };
      }
      
      if (call.call_status === 'error') {
        return {
          success: false,
          status: call.call_status,
          error: call.error_message,
        };
      }
      
      // Wait 5 seconds before checking again
      await new Promise(r => setTimeout(r, 5000));
    }
    
    return {
      success: false,
      status: 'timeout',
      error: 'Call did not complete within timeout',
    };
  }
}

export default RetellClient;

// CLI usage
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const client = new RetellClient();
  const [,, command, ...args] = process.argv;

  (async () => {
    switch (command) {
      case 'list':
        const calls = await client.listCalls();
        console.log(JSON.stringify(calls, null, 2));
        break;
      
      case 'get':
        const call = await client.getCall(args[0]);
        console.log(JSON.stringify(call, null, 2));
        break;
      
      case 'transcript':
        const transcript = await client.getTranscript(args[0]);
        console.log(transcript);
        break;
      
      default:
        console.log('Usage: node client.js <command> [args]');
        console.log('Commands: list, get <call_id>, transcript <call_id>');
    }
  })().catch(console.error);
}
