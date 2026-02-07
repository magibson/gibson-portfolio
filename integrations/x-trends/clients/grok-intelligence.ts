/**
 * Grok X Intelligence Client
 * 
 * Uses the Apify "Grok X Intelligence" actor which wraps xAI's Grok API
 * with the x_search tool for real X/Twitter data.
 * 
 * This is the RECOMMENDED approach - combines:
 * - xAI's Grok AI analysis
 * - Real X/Twitter data via x_search
 * - Easy automation through Apify
 * 
 * Actor: constant_quadruped/grok-x-intelligence
 * 
 * Pricing:
 * - Apify compute: ~$0.01-0.05 per run
 * - xAI tokens: ~1,000-10,000 tokens per run
 * - X Search: $5 per 1,000 searches
 */

import * as dotenv from 'dotenv';
import * as path from 'path';

// Load config
dotenv.config({ path: path.join(__dirname, '../config/xai.env') });
dotenv.config({ path: path.join(__dirname, '../config/apify.env') });

interface GrokIntelligenceConfig {
  apifyToken: string;
  xaiApiKey: string;
  xModel: string;
  chatModel: string;
}

// Tool types
type TrendCategory = 'general' | 'tech' | 'business' | 'sports' | 'entertainment';
type SentimentFilter = 'any' | 'positive' | 'negative' | 'neutral';
type IntentType = 'seeking_recommendation' | 'expressing_frustration' | 'comparing_options' | 'ready_to_switch' | 'asking_for_help';

interface TrendResult {
  type: 'tool_result';
  tool: string;
  success: boolean;
  result: {
    category: string;
    trends: Array<{
      topic: string;
      volume?: number;
      sentiment?: string;
      context?: string;
    }>;
    analysis?: string;
  };
  timestamp: string;
}

interface MonitorResult {
  type: 'tool_result';
  tool: string;
  success: boolean;
  result: {
    query: string;
    sentiment_summary: {
      positive: number;
      negative: number;
      neutral: number;
      score: number;
    };
    posts: Array<{
      text: string;
      author: string;
      sentiment: string;
      engagement: { likes: number; retweets: number };
      intent?: string;
      timestamp: string;
    }>;
    themes: string[];
  };
  timestamp: string;
}

interface IntentResult {
  type: 'tool_result';
  tool: string;
  success: boolean;
  result: {
    product_category: string;
    leads: Array<{
      text: string;
      author: string;
      intent_type: string;
      confidence: number;
      engagement: { likes: number; retweets: number };
      timestamp: string;
    }>;
    intent_breakdown: Record<string, number>;
  };
  timestamp: string;
}

class GrokIntelligenceClient {
  private config: GrokIntelligenceConfig;
  private actorId = 'constant_quadruped/grok-x-intelligence';
  private apifyBaseUrl = 'https://api.apify.com/v2';

  constructor(config?: Partial<GrokIntelligenceConfig>) {
    this.config = {
      apifyToken: config?.apifyToken || process.env.APIFY_TOKEN || '',
      xaiApiKey: config?.xaiApiKey || process.env.XAI_API_KEY || '',
      xModel: config?.xModel || 'grok-4-fast',
      chatModel: config?.chatModel || 'grok-2-latest',
    };

    if (!this.config.apifyToken) {
      throw new Error('APIFY_TOKEN is required. Get one at https://apify.com');
    }
    if (!this.config.xaiApiKey) {
      throw new Error('XAI_API_KEY is required. Get one at https://console.x.ai');
    }
  }

  /**
   * Get trending topics from X
   */
  async getTrends(options: {
    category?: TrendCategory;
    limit?: number;
  } = {}): Promise<TrendResult> {
    const { category = 'business', limit = 20 } = options;

    return this.runTool('grok_x_trends', {
      category,
      limit,
    });
  }

  /**
   * Monitor brand/topic mentions with sentiment analysis
   */
  async monitorBrand(options: {
    query: string;
    sentimentFilter?: SentimentFilter;
    minEngagement?: number;
    hoursBack?: number;
    limit?: number;
  }): Promise<MonitorResult> {
    const { 
      query, 
      sentimentFilter = 'any', 
      minEngagement = 0, 
      hoursBack = 24, 
      limit = 20 
    } = options;

    return this.runTool('grok_x_monitor', {
      query,
      sentiment_filter: sentimentFilter,
      min_engagement: minEngagement,
      hours_back: hoursBack,
      limit,
    });
  }

  /**
   * Find people expressing buying intent
   */
  async findLeadIntent(options: {
    productCategory: string;
    intentTypes?: IntentType[];
    excludeBrands?: string[];
    hoursBack?: number;
    limit?: number;
  }): Promise<IntentResult> {
    const {
      productCategory,
      intentTypes = ['seeking_recommendation', 'ready_to_switch'],
      excludeBrands = [],
      hoursBack = 48,
      limit = 25,
    } = options;

    return this.runTool('grok_x_intent', {
      product_category: productCategory,
      intent_types: intentTypes,
      exclude_brands: excludeBrands,
      hours_back: hoursBack,
      limit,
    });
  }

  /**
   * Compare brands competitively
   */
  async compareCompetitors(options: {
    brands: string[];
    aspect?: string;
    hoursBack?: number;
  }): Promise<any> {
    const { brands, aspect = 'general', hoursBack = 168 } = options;

    if (brands.length < 2 || brands.length > 5) {
      throw new Error('Must compare 2-5 brands');
    }

    return this.runTool('grok_x_compete', {
      brands,
      aspect,
      hours_back: hoursBack,
    });
  }

  /**
   * Raw X search
   */
  async searchX(query: string, limit = 50): Promise<any> {
    return this.runTool('grok_x_search', {
      query,
      limit,
    });
  }

  /**
   * Chat with Grok
   */
  async chat(message: string): Promise<any> {
    return this.runTool('grok_chat', {
      message,
    });
  }

  /**
   * Get financial trends specifically
   */
  async getFinancialTrends(): Promise<TrendResult> {
    return this.getTrends({ category: 'business', limit: 25 });
  }

  /**
   * Monitor financial advisor topics
   */
  async monitorAdvisorTopics(): Promise<MonitorResult> {
    return this.monitorBrand({
      query: 'financial advisor OR wealth management OR retirement planning OR 401k',
      hoursBack: 48,
      limit: 30,
    });
  }

  /**
   * Find people looking for financial advice
   */
  async findFinancialLeads(): Promise<IntentResult> {
    return this.findLeadIntent({
      productCategory: 'financial advisor services',
      intentTypes: ['seeking_recommendation', 'asking_for_help', 'comparing_options'],
      hoursBack: 72,
      limit: 30,
    });
  }

  /**
   * Run a tool through the Apify actor
   */
  private async runTool(toolName: string, toolArgs: Record<string, any>): Promise<any> {
    // Start the actor run
    const runResponse = await fetch(
      `${this.apifyBaseUrl}/acts/${this.actorId}/runs?token=${this.config.apifyToken}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          xaiApiKey: this.config.xaiApiKey,
          model: this.config.chatModel,
          xModel: this.config.xModel,
          maxTokens: 4096,
          temperature: 0.7,
          toolCall: {
            name: toolName,
            arguments: toolArgs,
          },
        }),
      }
    );

    if (!runResponse.ok) {
      const error = await runResponse.text();
      throw new Error(`Apify API error: ${runResponse.status} - ${error}`);
    }

    const runData = await runResponse.json();
    const runId = runData.data.id;

    // Wait for completion
    return this.waitForRun(runId);
  }

  /**
   * Wait for an Apify run to complete
   */
  private async waitForRun(runId: string, timeoutMs = 120000): Promise<any> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeoutMs) {
      const statusResponse = await fetch(
        `${this.apifyBaseUrl}/actor-runs/${runId}?token=${this.config.apifyToken}`
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
          `${this.apifyBaseUrl}/datasets/${datasetId}/items?token=${this.config.apifyToken}`
        );

        if (!dataResponse.ok) {
          throw new Error(`Failed to get dataset: ${dataResponse.status}`);
        }

        const data = await dataResponse.json();
        return data[0] || data;
      } else if (status === 'FAILED' || status === 'ABORTED') {
        throw new Error(`Run ${status}: ${statusData.data.statusMessage || 'Unknown error'}`);
      }

      // Wait 3 seconds before checking again
      await new Promise(resolve => setTimeout(resolve, 3000));
    }

    throw new Error(`Run timed out after ${timeoutMs}ms`);
  }
}

// Export
export { GrokIntelligenceClient, GrokIntelligenceConfig, TrendResult, MonitorResult, IntentResult };

// CLI usage
if (require.main === module) {
  const client = new GrokIntelligenceClient();

  console.log('🤖 Grok X Intelligence Demo\n');
  console.log('Fetching business trends from X...\n');

  client.getFinancialTrends()
    .then(result => {
      console.log('📊 Business Trends:');
      console.log('=' .repeat(50));
      if (result.result?.trends) {
        for (const trend of result.result.trends) {
          console.log(`• ${trend.topic}${trend.volume ? ` (${trend.volume} posts)` : ''}`);
        }
      } else {
        console.log(JSON.stringify(result, null, 2));
      }
      console.log('\n⏰ Generated:', result.timestamp);
    })
    .catch(err => {
      console.error('Error:', err.message);
      console.log('\nMake sure both APIFY_TOKEN and XAI_API_KEY are set.');
      process.exit(1);
    });
}
