/**
 * Apify X Trends Scraper Client
 * 
 * Uses Apify actors to scrape trending topics from X (Twitter).
 * This is the CHEAPEST option - ~$0.01 per 1,000 trends.
 * 
 * Actors used:
 * - eunit/x-twitter-trends-scraper - Full featured
 * - fastcrawler/x-twitter-trends-scraper-2025 - Updated 2025 version
 */

import * as dotenv from 'dotenv';
import * as path from 'path';

// Load config
dotenv.config({ path: path.join(__dirname, '../config/apify.env') });

interface ApifyConfig {
  token: string;
  actor: string;
  defaultLocation: string;
  timeoutMs: number;
}

interface Trend {
  rank: number;
  name: string;
  tweetCount: string | number;
  link: string;
}

interface TrendsResult {
  location: string;
  scrapedAt: Date;
  trends: Trend[];
  tagCloud?: Array<{ name: string; link: string }>;
  timeline?: Array<{
    datetime: string;
    timestamp: string;
    trends: Trend[];
  }>;
}

class ApifyTrendsClient {
  private config: ApifyConfig;
  private baseUrl = 'https://api.apify.com/v2';

  constructor(config?: Partial<ApifyConfig>) {
    this.config = {
      token: config?.token || process.env.APIFY_TOKEN || '',
      actor: config?.actor || process.env.APIFY_TRENDS_ACTOR || 'eunit/x-twitter-trends-scraper',
      defaultLocation: config?.defaultLocation || process.env.APIFY_DEFAULT_LOCATION || 'united-states',
      timeoutMs: config?.timeoutMs || parseInt(process.env.APIFY_TIMEOUT_MS || '60000'),
    };

    if (!this.config.token) {
      throw new Error('APIFY_TOKEN is required. Get one at https://apify.com');
    }
  }

  /**
   * Get trending topics for a location
   * 
   * @param location - Location string (e.g., "united-states", "united-states/new-york")
   */
  async getTrends(location?: string): Promise<TrendsResult> {
    const loc = location || this.config.defaultLocation;
    
    // Start the actor run
    const runResponse = await fetch(
      `${this.baseUrl}/acts/${this.config.actor}/runs?token=${this.config.token}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          country: loc,
        }),
      }
    );

    if (!runResponse.ok) {
      const error = await runResponse.text();
      throw new Error(`Apify API error: ${runResponse.status} - ${error}`);
    }

    const runData = await runResponse.json();
    const runId = runData.data.id;

    // Wait for the run to complete
    const result = await this.waitForRun(runId);
    
    return this.parseResult(result, loc);
  }

  /**
   * Get US trends (convenience method)
   */
  async getUSTrends(): Promise<TrendsResult> {
    return this.getTrends('united-states');
  }

  /**
   * Get worldwide trends
   */
  async getWorldwideTrends(): Promise<TrendsResult> {
    return this.getTrends('worldwide');
  }

  /**
   * Get trends for multiple locations
   */
  async getMultiLocationTrends(locations: string[]): Promise<TrendsResult[]> {
    const results = await Promise.all(
      locations.map(loc => this.getTrends(loc).catch(err => {
        console.error(`Error fetching trends for ${loc}:`, err.message);
        return null;
      }))
    );
    return results.filter((r): r is TrendsResult => r !== null);
  }

  /**
   * Filter trends by keywords
   */
  filterTrends(trends: Trend[], keywords: string[]): Trend[] {
    const lowerKeywords = keywords.map(k => k.toLowerCase());
    return trends.filter(trend => {
      const lowerName = trend.name.toLowerCase();
      return lowerKeywords.some(kw => lowerName.includes(kw));
    });
  }

  /**
   * Get financial-related trends
   */
  async getFinancialTrends(location?: string): Promise<Trend[]> {
    const result = await this.getTrends(location);
    const financialKeywords = [
      'stock', 'market', 'invest', 'trading', 'crypto', 'bitcoin', 'btc', 'eth',
      'fed', 'interest rate', 'inflation', 'recession', 'earnings', 'ipo',
      's&p', 'dow', 'nasdaq', 'tesla', 'apple', 'nvidia', 'finance', 'money',
      '401k', 'retirement', 'wealth', 'dividend', 'portfolio', 'hedge',
    ];
    return this.filterTrends(result.trends, financialKeywords);
  }

  /**
   * Wait for an Apify run to complete
   */
  private async waitForRun(runId: string): Promise<any> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < this.config.timeoutMs) {
      const statusResponse = await fetch(
        `${this.baseUrl}/actor-runs/${runId}?token=${this.config.token}`
      );
      
      if (!statusResponse.ok) {
        throw new Error(`Failed to check run status: ${statusResponse.status}`);
      }

      const statusData = await statusResponse.json();
      const status = statusData.data.status;

      if (status === 'SUCCEEDED') {
        // Get the dataset
        const datasetId = statusData.data.defaultDatasetId;
        const dataResponse = await fetch(
          `${this.baseUrl}/datasets/${datasetId}/items?token=${this.config.token}`
        );
        
        if (!dataResponse.ok) {
          throw new Error(`Failed to get dataset: ${dataResponse.status}`);
        }

        return dataResponse.json();
      } else if (status === 'FAILED' || status === 'ABORTED') {
        throw new Error(`Apify run ${status}: ${statusData.data.statusMessage || 'Unknown error'}`);
      }

      // Wait 2 seconds before checking again
      await new Promise(resolve => setTimeout(resolve, 2000));
    }

    throw new Error(`Apify run timed out after ${this.config.timeoutMs}ms`);
  }

  /**
   * Parse Apify result into our format
   */
  private parseResult(data: any[], location: string): TrendsResult {
    // The response format varies by actor, handle common cases
    const item = data[0] || {};
    
    const trends: Trend[] = [];
    
    // Handle table_data format
    if (item.table_data) {
      for (const t of item.table_data) {
        trends.push({
          rank: parseInt(t.rank) || trends.length + 1,
          name: t.name || t.hashtag || '',
          tweetCount: t.tweet_count || t.volume || 'N/A',
          link: t.link || `https://twitter.com/search?q=${encodeURIComponent(t.name || '')}`,
        });
      }
    }
    
    // Handle trends array format
    if (item.trends) {
      for (const t of item.trends) {
        if (!trends.find(existing => existing.name === t.name)) {
          trends.push({
            rank: t.rank || trends.length + 1,
            name: t.name || t.hashtag || '',
            tweetCount: t.tweet_count || t.volume || 'N/A',
            link: t.link || `https://twitter.com/search?q=${encodeURIComponent(t.name || '')}`,
          });
        }
      }
    }

    // Handle timeline format
    if (item.timeline?.[0]?.trends) {
      for (const t of item.timeline[0].trends) {
        if (!trends.find(existing => existing.name === t.name)) {
          trends.push({
            rank: t.rank || trends.length + 1,
            name: t.name || t.hashtag || '',
            tweetCount: t.tweet_count || t.volume || 'N/A',
            link: t.link || `https://twitter.com/search?q=${encodeURIComponent(t.name || '')}`,
          });
        }
      }
    }

    return {
      location,
      scrapedAt: new Date(item.scraped_at || Date.now()),
      trends: trends.slice(0, 50), // Top 50
      tagCloud: item.tag_cloud,
      timeline: item.timeline,
    };
  }
}

// Export for use
export { ApifyTrendsClient, ApifyConfig, Trend, TrendsResult };

// CLI usage
if (require.main === module) {
  const client = new ApifyTrendsClient();
  
  console.log('🔍 Fetching X trends via Apify...\n');
  
  client.getUSTrends()
    .then(result => {
      console.log(`📍 Location: ${result.location}`);
      console.log(`⏰ Scraped: ${result.scrapedAt.toISOString()}`);
      console.log(`\n📊 Top 20 Trends:`);
      console.log('=' .repeat(50));
      
      for (const trend of result.trends.slice(0, 20)) {
        console.log(`${trend.rank}. ${trend.name} (${trend.tweetCount} tweets)`);
      }
    })
    .catch(err => {
      console.error('Error:', err.message);
      process.exit(1);
    });
}
