# X (Twitter) Trend Monitoring - Options for Matt

## TL;DR - Our Recommendation

**For trend monitoring on a budget: Use Apify's X Trends Scraper**
- Cost: ~$0.01 per 1,000 trends (essentially free for basic use)
- No API keys needed, works out of the box
- Location-specific trends (US, specific cities, etc.)

**If you want AI analysis + trends: Use xAI Grok API with X Search**
- Cost: $5 per 1,000 searches + token costs (~$2-5/input, $10-15/output per million)
- Can search X posts AND analyze them with Grok AI
- More powerful but more expensive

---

## Option Comparison

| Option | Monthly Cost | Best For | Difficulty |
|--------|-------------|----------|------------|
| Apify Trends Scraper | ~$5-10/mo | Just trending topics | Easy |
| xAI Grok + X Search | ~$50-100/mo | AI-powered trend analysis | Medium |
| TwitterAPI.io | ~$15-50/mo | Tweet data + search | Medium |
| SociaVault | ~$30-80/mo | Multi-platform scraping | Medium |
| RapidAPI Trends | Free-$10/mo | Simple trends only | Easy |
| Official X API Basic | $200/mo | Full API access | Hard |
| Official X API Pro | $5,000/mo | High-volume needs | Enterprise |

---

## Detailed Breakdown

### 1. Official X API (Twitter) ❌ NOT RECOMMENDED

**Pricing (2025):**
- Free: 500 posts/month (write), 100 reads/month - basically useless
- Basic: **$200/month** - 50k posts, 15k reads
- Pro: **$5,000/month** - 300k posts, 1M reads  
- Enterprise: **$42,000+/month** - Custom limits

**Verdict:** Way too expensive for trend monitoring. The Basic tier doesn't even include the trends endpoint. Skip this.

---

### 2. xAI Grok API with X Search ✅ RECOMMENDED IF YOU WANT AI

**What it is:** xAI's Grok AI with built-in X search capabilities.

**Pricing:**
- X Search tool: **$5 per 1,000 calls**
- Token costs (Grok 3): ~$2/M input, $10/M output
- Token costs (Grok 4): ~$6/M input, $30/M output

**Pros:**
- Search X posts directly through the API
- Get AI analysis/summarization of trends
- Can ask "What's trending in finance?" and get intelligent answers
- Understands context, can filter by topic

**Cons:**
- No direct "trends" endpoint - you search for topics
- Token costs add up for heavy analysis
- Requires xAI API key (sign up at console.x.ai)

**Use case:** "Show me what financial advisors are talking about on X today and summarize the sentiment"

**Config:** See `config/xai.env.example`

---

### 3. Apify X Trends Scraper ✅ RECOMMENDED FOR BUDGET

**What it is:** Web scraper that extracts trending topics from X.

**Pricing:**
- Apify free tier: 5 actor runs/month
- Pay-as-you-go: **~$0.01 per 1,000 results**
- Typical monthly cost: $5-10 for daily trend checks

**Actors available:**
- `eunit/x-twitter-trends-scraper` - Full featured
- `fastcrawler/x-twitter-trends-scraper-2025` - Updated 2025 version
- `eunit/x-twitter-trends-ppe` - Pay-per-event pricing

**What you get:**
- Top 50 trending topics per location
- Tweet counts and ranks
- Hourly trend history
- 60+ countries and cities supported

**Pros:**
- Incredibly cheap
- No X API key needed
- Location-specific (US, New York, etc.)
- Export to JSON/CSV
- Can schedule automatic runs

**Cons:**
- Just trends, not full tweet content
- Scraping (could break if X changes)
- No AI analysis (just raw data)

**Use case:** "Get the top 50 US trends every 6 hours"

**Config:** See `config/apify.env.example`

---

### 4. TwitterAPI.io ✅ GOOD ALTERNATIVE

**What it is:** Third-party API that provides X data at 97% less cost than official API.

**Pricing:**
- Tweets: **$0.15 per 1,000**
- Profiles: **$0.18 per 1,000**
- Pay-as-you-go, no monthly commitment

**Pros:**
- Full tweet data, not just trends
- Simple REST API
- Can search by keywords
- Much cheaper than official API

**Cons:**
- No dedicated trends endpoint (use search)
- Still costs money (vs Apify's near-free)
- Third-party (could shut down)

**Use case:** "Search for tweets mentioning 'S&P 500' in the last hour"

---

### 5. RapidAPI Twitter Trends 🆓 FREE OPTION

**What it is:** Various Twitter trends APIs on RapidAPI marketplace.

**Options:**
- `twitter-trends5` - Free tier, top 100 trends
- `twitter-trend` - Research/collection focused
- Updated every 30 minutes

**Pricing:**
- Free tier: Limited calls/month
- Basic: ~$10/month for more calls

**Pros:**
- Free tier available
- Simple REST API
- Quick to integrate

**Cons:**
- Limited to trends only
- Rate limits on free tier
- Less reliable than Apify

---

## What Matt Might Want to Track

### General Trends
- US trending topics
- Global trending topics
- Trending hashtags

### Financial/Investing Trends
Best approach: Use xAI Grok with X Search
- Query: "What are people talking about regarding stocks, investing, markets?"
- Can filter for sentiment (bullish/bearish)
- Get summaries instead of raw tweets

### Topics for Financial Advisors
- "retirement planning"
- "401k"
- "financial planning"
- "wealth management"
- Competitor mentions
- Industry news

### Own Mentions (if building presence)
- Track @mentions
- Track name mentions
- Monitor engagement
- Best done with TwitterAPI.io or full search scraper

---

## Our Setup

### Files in this folder:
```
x-trends/
├── README.md                 # This file
├── config/
│   ├── xai.env.example      # xAI API config template
│   └── apify.env.example    # Apify config template
├── clients/
│   ├── xai-trends.ts        # xAI Grok X Search client
│   ├── apify-trends.ts      # Apify trends scraper client
│   └── rapidapi-trends.ts   # RapidAPI fallback client
└── examples/
    └── demo.ts              # Usage examples
```

---

## Quick Start

### Option A: Apify (Cheapest)

1. Sign up at https://apify.com (free)
2. Get your API token from Settings
3. Copy `config/apify.env.example` to `config/apify.env`
4. Add your token
5. Run the client

### Option B: xAI Grok (Most Powerful)

1. Sign up at https://console.x.ai
2. Create an API key
3. Copy `config/xai.env.example` to `config/xai.env`
4. Add your API key
5. Run the client

---

## Next Steps

1. **Decide what you want:** Just trends? Or AI analysis?
2. **Sign up for chosen service:** Apify or xAI
3. **Configure API keys:** Fill in the env files
4. **Test the clients:** Run the demo script
5. **Set up automation:** Cron job or heartbeat check

Questions? Let me know what direction you want to go!
