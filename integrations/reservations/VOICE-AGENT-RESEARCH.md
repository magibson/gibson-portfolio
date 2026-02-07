# AI Voice Agent Research: Restaurant Reservations

> **Use Case:** Personal AI assistant to call restaurants and make reservations on Matt's behalf  
> **Volume:** 5-20 calls/month  
> **Existing Account:** ElevenLabs  
> **Research Date:** January 2026

---

## Executive Summary

**Recommendation: Retell AI** (Best value for low-volume personal use)

For making restaurant reservation calls, **Retell AI** offers the best balance of:
- Low per-minute cost (~$0.13-0.15/min all-in)
- No monthly minimums
- $10 free credit to start
- Uses ElevenLabs voices under the hood
- Good documentation and templates

**Runner-up: ElevenLabs Agents** if you value staying in one ecosystem and don't mind paying ~50% more per minute.

---

## Platform Comparison

### 1. ElevenLabs Conversational AI (Agents)

**Pricing:**
- $0.10/min base (Creator/Pro plans) — recently cut from ~$0.20/min
- $0.08/min on Business annual plan
- LLM costs currently absorbed but will eventually be added
- Requires existing ElevenLabs subscription for best rates

**Pros:**
- ✅ Matt already has an account
- ✅ Best-in-class voice quality and naturalness
- ✅ 5,000+ voices, 31 languages
- ✅ Excellent documentation
- ✅ Supports outbound calling via Twilio integration
- ✅ Visual workflow builder

**Cons:**
- ❌ Higher cost than competitors (~$0.15-0.18/min with LLM when unbundled)
- ❌ Need to manage Twilio separately for phone numbers
- ❌ No free tier for Conversational AI (only TTS)

**For 10 calls/month @ 3 min avg = 30 min → $3-5.40/month**

---

### 2. Retell AI ⭐ RECOMMENDED

**Pricing:**
- $0.07/min conversation engine (with ElevenLabs/Cartesia voices)
- $0.006-0.05/min LLM (GPT-4o mini = $0.006, GPT-4o = $0.05)
- $0.015/min telephony (Retell Twilio)
- **Total: ~$0.09-0.14/min** depending on LLM choice
- $2/month per phone number
- **$10 free credit to start**
- 20 free concurrent calls

**Pros:**
- ✅ Lowest all-in cost for quality
- ✅ Uses ElevenLabs voices (same quality Matt expects)
- ✅ No monthly minimums - true pay-as-you-go
- ✅ $10 free credit = ~70+ minutes free
- ✅ Great for low-volume personal use
- ✅ SOC 2, HIPAA compliant (overkill for personal use, but solid)
- ✅ Good reddit reviews for turn-taking quality

**Cons:**
- ❌ No visual flow builder (API/config only)
- ❌ Need to set up prompts yourself

**For 10 calls/month @ 3 min avg = 30 min → $2.70-4.20/month + $2 phone = ~$5-6/month**

---

### 3. Bland AI

**Pricing (as of Dec 2025):**
- Start (free): $0.14/min, 100 calls/day limit
- Build ($299/mo): $0.12/min, 2,000 calls/day
- Scale ($499/mo): $0.11/min, 5,000 calls/day
- Phone numbers: $15/month
- $0.015 minimum per failed call

**Pros:**
- ✅ Simple pricing structure
- ✅ Good for high-volume businesses
- ✅ Includes LLM in per-minute rate
- ✅ Voice cloning available

**Cons:**
- ❌ Free tier is $0.14/min — more expensive than Retell
- ❌ No free credits
- ❌ Phone numbers cost $15/mo vs Retell's $2/mo
- ❌ Better suited for business than personal use

**For 10 calls/month @ 3 min avg = 30 min → $4.20/month + $15 phone = ~$19/month**

---

### 4. Vapi

**Pricing:**
- $0.05/min orchestration (base)
- **Hidden costs:** STT, LLM, TTS all billed separately
- Real cost: **$0.13-0.33/min** when you add all components
- Concurrency must be pre-purchased

**Pros:**
- ✅ Most modular/flexible platform
- ✅ Supports any combination of STT/LLM/TTS providers
- ✅ 100+ languages
- ✅ Good for developers who want full control

**Cons:**
- ❌ Advertised $0.05/min is misleading — actual costs much higher
- ❌ Complex setup with multiple providers
- ❌ Better for technical teams building products
- ❌ Billing across 4-6 different providers is confusing

**For 10 calls/month @ 3 min avg = 30 min → $4-10/month** (highly variable)

---

### 5. Synthflow

**Pricing:**
- Starter: $29/mo base + $0.12-0.13/min overage
- Enterprise: $0.07-0.08/min flat
- 14-day free trial

**Pros:**
- ✅ No-code visual builder (easiest to set up)
- ✅ Restaurant reservation template exists
- ✅ Bundled pricing (simpler)
- ✅ Good for non-technical users

**Cons:**
- ❌ $29/mo minimum even for low usage
- ❌ Overage rates are high ($0.12-0.13/min)
- ❌ Basic features locked behind higher tiers

**For 10 calls/month @ 3 min avg = $29/month minimum** — overkill for personal use

---

### 6. Air AI

**Pricing:**
- $0.19/min for GPT-4o voice calls
- Usage-based, no monthly minimums
- 14-day free trial

**Pros:**
- ✅ Focused on conversational AI
- ✅ Free trial to test
- ✅ No monthly commitment

**Cons:**
- ❌ Higher per-minute rate
- ❌ Less established than competitors

---

### 7. Lindy AI (Alternative)

**Pricing:**
- Free tier available
- $0-$299/mo depending on usage
- General automation platform, not voice-specific

**Pros:**
- ✅ Can orchestrate voice calls + other tasks
- ✅ No-code builder
- ✅ Free tier exists

**Cons:**
- ❌ Not specialized for voice
- ❌ May need to integrate with other voice providers

---

## Cost Comparison Summary

| Platform | Per-Minute (All-In) | Phone # Cost | Monthly Min | 30 min/mo Cost |
|----------|---------------------|--------------|-------------|----------------|
| **Retell AI** | $0.09-0.14 | $2/mo | $0 | **~$5-6** |
| ElevenLabs | $0.10-0.18 | Via Twilio | Subscription | ~$5-8 |
| Bland AI | $0.14 (free tier) | $15/mo | $0 | ~$19 |
| Vapi | $0.13-0.33 | Varies | $0 | ~$6-12 |
| Synthflow | $0.12-0.13 | Included | $29/mo | ~$29+ |

---

## Restaurant Reservation Call Flow

A typical outbound reservation call needs to handle:

1. **Introduction**
   - "Hi, I'm calling to make a reservation at [Restaurant Name]"

2. **Core Details**
   - Date and time requested
   - Party size
   - Name for the reservation
   - Contact phone number

3. **Negotiation**
   - Handle "that time is unavailable"
   - Accept alternative times
   - Ask about outdoor/indoor seating
   - Special requests (birthday, anniversary, dietary needs)

4. **Confirmation**
   - Repeat back the confirmed details
   - Ask about cancellation policy if needed
   - Thank them

5. **Edge Cases**
   - Restaurant is closed
   - No availability
   - Need to speak to manager
   - Put on hold
   - Call back requested

---

## Existing Templates & Examples

### n8n Workflow Template
There's a ready-made n8n template: **"Automated property & restaurant bookings with AI voice calls via Telegram"**
- URL: https://n8n.io/workflows/9850
- Integrates with Telegram for commands
- Checks calendar for conflicts
- Places outbound calls
- Returns confirmation summaries

This could be adapted for Matt's use case!

### Synthflow Restaurant Demo
Synthflow has a working demo "Laura" for restaurant reservations:
- Handles greetings, occasion questions
- Books tables with party size
- Confirms reservation details

Can be used as a prompt reference.

---

## Gotchas & Limitations

### Regulatory (TCPA)
- ⚠️ FCC ruled AI-generated voices are "artificial" under TCPA
- **However:** TCPA applies to telemarketing/commercial calls
- Personal reservation calls are **not regulated** under TCPA
- You're calling businesses, not consumers

### Spam/Blocking
- Restaurant phones may flag unknown numbers
- Consider using a verified number or CNAM registration
- Retell offers "Branded Call" feature ($0.10/outbound call) to show business name

### Call Quality
- Some restaurants have bad phone systems or hold music
- Noisy kitchens can confuse STT
- May need to handle "please hold" scenarios

### Latency
- Sub-500ms response time is critical for natural conversation
- All top platforms (Retell, ElevenLabs, Vapi) meet this
- Bland AI has some reported latency issues

---

## Final Recommendation

### For Matt's Use Case (5-20 calls/month, personal use):

**🥇 Primary: Retell AI**
- Start with $10 free credit (~70 min)
- ~$0.13/min all-in with GPT-4o mini + ElevenLabs voice
- $2/mo phone number
- Estimated cost: **$5-10/month** for typical usage
- Uses the same ElevenLabs voices Matt knows

**🥈 Alternative: ElevenLabs Agents**
- If you value staying in one ecosystem
- Better if you're already on a higher ElevenLabs plan
- ~50% premium over Retell but simpler billing

**❌ Skip:**
- Synthflow ($29/mo minimum is overkill)
- Bland AI ($15/mo phone number + higher per-minute)
- Vapi (too complex for simple use case)

---

## Next Steps

1. **Sign up for Retell AI** (free, get $10 credit)
2. **Create a restaurant reservation agent** with the prompt template below
3. **Buy a phone number** ($2/mo)
4. **Test with a few local restaurants**
5. **Optionally:** Integrate with n8n or make-a-call script

### Sample Prompt for Restaurant Reservation Agent

```
You are a friendly assistant calling to make a restaurant reservation on behalf of Matt.

INFORMATION TO PROVIDE:
- Name: Matt [Last Name]
- Party size: {{party_size}}
- Preferred date: {{date}}
- Preferred time: {{time}}
- Phone number: {{callback_number}}

BEHAVIOR:
- Be polite, concise, and natural
- If the requested time isn't available, ask what times ARE available and accept a reasonable alternative
- Confirm all details at the end of the call
- If put on hold, wait patiently (up to 2 minutes)
- If no availability at all, ask about waitlist or alternative dates

CONVERSATION FLOW:
1. Introduce yourself: "Hi, I'm calling to make a dinner reservation."
2. Provide details when asked
3. Negotiate timing if needed
4. Confirm the reservation details
5. Thank them and end the call

END THE CALL when:
- Reservation is confirmed
- Restaurant says they're fully booked with no alternatives
- You've been on hold for more than 2 minutes
```

---

## References

- Retell AI Pricing: https://www.retellai.com/pricing
- ElevenLabs Agents: https://elevenlabs.io/docs/agents-platform/overview
- Bland AI Billing: https://docs.bland.ai/platform/billing
- Voice Platform Comparison (Softcery): https://softcery.com/lab/choosing-the-right-voice-agent-platform-in-2025
- n8n Booking Template: https://n8n.io/workflows/9850
