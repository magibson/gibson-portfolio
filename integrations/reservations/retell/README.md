# Retell AI - Restaurant Reservation Integration

Makes phone calls to restaurants to book reservations on your behalf.

## Setup (One-time)

### 1. Create Retell Account
1. Go to https://www.retellai.com/
2. Sign up (free, get $10 credit)
3. Go to Dashboard → API Keys
4. Create a new API key, copy it

### 2. Configure
```bash
cp .env.example .env
# Edit .env and add your RETELL_API_KEY
```

### 3. Buy a Phone Number
In Retell Dashboard → Phone Numbers → Buy Number
- Pick a local area code
- $2/month

### 4. Create the Agent
```bash
node setup-agent.js
```

## Usage

### Via Jarvis
Just ask:
- "Book me a table at Carbone for 2 on Saturday at 7pm"
- "Make a reservation at The Dutch, 4 people, Friday 8pm"

### Via CLI
```bash
node call.js --restaurant "Carbone" --phone "+12125551234" --date "2026-02-01" --time "19:00" --party 2
```

## How It Works

1. You request a reservation
2. Jarvis extracts: restaurant name, phone, date, time, party size
3. Retell AI calls the restaurant
4. AI agent speaks with host, negotiates timing if needed
5. Returns confirmation or alternative options

## Cost

- ~$0.13/minute for calls
- Average reservation call: 2-3 minutes
- **Typical cost: $0.25-0.40 per reservation**

## Files

- `client.js` - Retell API client
- `call.js` - CLI to make calls
- `setup-agent.js` - Create/update the reservation agent
- `agent-prompt.txt` - The AI agent's instructions
