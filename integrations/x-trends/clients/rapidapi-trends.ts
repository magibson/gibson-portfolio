/**
 * RapidAPI Twitter Trends Client
 * 
 * Uses RapidAPI's Twitter Trends API as a simple fallback.
 * Has a free tier with limited calls.
 * 
 * API: https://rapidapi.com/brkygt88/api/twitter-trends5
 */

import * as dotenv from 'dotenv';
import * as path from 'path';

// Load config
dotenv.config({ path: path.join(__dirname, '../config/rapidapi.env') });

interface RapidAPIConfig {
  apiKey: string;
  host: string;
  defaultWoeid: number;
}

interface Trend {
  rank: number;
  name: string;
  tweetCount: string | number;
  url: string;
}

interface TrendsResult {
  woeid: number;
  locationName?: string;
  trends: Trend[];
  fetchedAt: Date;
}

// Common WOEID values
const WOEID = {
  WORLDWIDE: 1,
  UNITED_STATES: 23424977,
  NEW_YORK: 2459115,
  LOS_ANGELES: 2442047,
  SAN_FRANCISCO: 2487956,
  CHICAGO: 2379574,
  MIAMI: 2450022,
  LONDON: 44418,
  PARIS: 615702,
  TOKYO: 1118370,
} as const;

class RapidAPITrendsClient {
  private config: RapidAPIConfig;
  
  constructor(config?: Partial<RapidAPIConfig>) {
    this.config = {
      apiKey: config?.apiKey || process.env.RAPIDAPI_KEY || '',
      host: config?.host || process.env.RAPIDAPI_HOST || 'twitter-trends5.p.rapidapi.com',
      defaultWoeid: config?.defaultWoeid || parseInt(process.env.RAPIDAPI_DEFAULT_WOEID || '23424977'),
    };

    if (!this.config.apiKey) {
      throw new Error('RAPIDAPI_KEY is required. Get one at https://rapidapi.com');
    }
  }

  /**
   * Get trending topics for a location by WOEID
   * 
   * @param woeid - Where On Earth ID (use WOEID constants)
   */
  async getTrends(woeid?: number): Promise<TrendsResult> {
    const location = woeid || this.config.defaultWoeid;
    
    const response = await fetch(
      `https://${this.config.host}/twitter-trends?woeid=${location}`,
      {
        method: 'GET',
        headers: {
          'X-RapidAPI-Key': this.config.apiKey,
          'X-RapidAPI-Host': this.config.host,
        },
      }
    );

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`RapidAPI error: ${response.status} - ${error}`);
    }

    const data = await response.json();
    return this.parseResult(data, location);
  }

  /**
   * Get US trends
   */
  async getUSTrends(): Promise<TrendsResult> {
    return this.getTrends(WOEID.UNITED_STATES);
  }

  /**
   * Get worldwide trends
   */
  async getWorldwideTrends(): Promise<TrendsResult> {
    return this.getTrends(WOEID.WORLDWIDE);
  }

  /**
   * Get New York trends
   */
  async getNewYorkTrends(): Promise<TrendsResult> {
    return this.getTrends(WOEID.NEW_YORK);
  }

  /**
   * Parse RapidAPI response
   */
  private parseResult(data: any, woeid: number): TrendsResult {
    const trends: Trend[] = [];
    
    // Handle different response formats
    const trendsList = data.trends || data[0]?.trends || data;
    
    if (Array.isArray(trendsList)) {
      for (let i = 0; i < trendsList.length; i++) {
        const t = trendsList[i];
        trends.push({
          rank: i + 1,
          name: t.name || t.query || '',
          tweetCount: t.tweet_volume || t.tweet_count || 'N/A',
          url: t.url || `https://twitter.com/search?q=${encodeURIComponent(t.name || '')}`,
        });
      }
    }

    return {
      woeid,
      locationName: this.getLocationName(woeid),
      trends,
      fetchedAt: new Date(),
    };
  }

  /**
   * Get human-readable location name from WOEID
   */
  private getLocationName(woeid: number): string {
    const names: Record<number, string> = {
      1: 'Worldwide',
      23424977: 'United States',
      2459115: 'New York',
      2442047: 'Los Angeles',
      2487956: 'San Francisco',
      2379574: 'Chicago',
      2450022: 'Miami',
      44418: 'London',
      615702: 'Paris',
      1118370: 'Tokyo',
    };
    return names[woeid] || `WOEID ${woeid}`;
  }
}

// Export for use
export { RapidAPITrendsClient, RapidAPIConfig, Trend, TrendsResult, WOEID };

// CLI usage
if (require.main === module) {
  const client = new RapidAPITrendsClient();
  
  console.log('🔍 Fetching X trends via RapidAPI...\n');
  
  client.getUSTrends()
    .then(result => {
      console.log(`📍 Location: ${result.locationName} (WOEID: ${result.woeid})`);
      console.log(`⏰ Fetched: ${result.fetchedAt.toISOString()}`);
      console.log(`\n📊 Top 20 Trends:`);
      console.log('='.repeat(50));
      
      for (const trend of result.trends.slice(0, 20)) {
        console.log(`${trend.rank}. ${trend.name} (${trend.tweetCount} tweets)`);
      }
    })
    .catch(err => {
      console.error('Error:', err.message);
      process.exit(1);
    });
}
