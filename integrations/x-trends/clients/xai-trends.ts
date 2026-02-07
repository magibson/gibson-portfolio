/**
 * xAI Grok API Client for X Trend Analysis
 * 
 * Uses Grok with X Search tool to analyze Twitter/X trends.
 * This is more powerful than simple scraping - it provides AI analysis.
 * 
 * Pricing:
 * - X Search: $5 per 1,000 calls
 * - Tokens: ~$2-6/M input, $10-30/M output depending on model
 */

import * as dotenv from 'dotenv';
import * as path from 'path';

// Load config
dotenv.config({ path: path.join(__dirname, '../config/xai.env') });

interface XAIConfig {
  apiKey: string;
  model: string;
  enableXSearch: boolean;
  enableWebSearch: boolean;
}

interface TrendAnalysis {
  query: string;
  trends: Array<{
    topic: string;
    summary: string;
    sentiment?: 'positive' | 'negative' | 'neutral' | 'mixed';
    relevance?: string;
  }>;
  analysis: string;
  timestamp: Date;
}

class XAITrendsClient {
  private config: XAIConfig;
  private baseUrl = 'https://api.x.ai/v1';

  constructor(config?: Partial<XAIConfig>) {
    this.config = {
      apiKey: config?.apiKey || process.env.XAI_API_KEY || '',
      model: config?.model || process.env.XAI_MODEL || 'grok-3-mini',
      enableXSearch: config?.enableXSearch ?? process.env.XAI_ENABLE_X_SEARCH === 'true',
      enableWebSearch: config?.enableWebSearch ?? process.env.XAI_ENABLE_WEB_SEARCH === 'true',
    };

    if (!this.config.apiKey) {
      throw new Error('XAI_API_KEY is required. Get one at https://console.x.ai');
    }
  }

  /**
   * Get trending topics with AI analysis
   * 
   * @param query - What to search for (e.g., "financial news", "stock market")
   * @param options - Additional options
   */
  async analyzeTrends(query: string, options: {
    maxResults?: number;
    timeframe?: 'today' | 'this_week' | 'recent';
    sentiment?: boolean;
  } = {}): Promise<TrendAnalysis> {
    const { maxResults = 10, timeframe = 'today', sentiment = true } = options;

    const systemPrompt = `You are a trend analyst. When given a topic, use the X Search tool to find what people are currently discussing about it on X (Twitter). 

Analyze the results and provide:
1. The main trending topics/themes you found
2. A brief summary of each topic
3. ${sentiment ? 'The general sentiment (positive/negative/neutral/mixed)' : ''}
4. An overall analysis of what this means

Be concise but informative. Focus on the most relevant and recent discussions.`;

    const userPrompt = `What are people talking about on X regarding "${query}" ${timeframe === 'today' ? 'today' : timeframe === 'this_week' ? 'this week' : 'recently'}? Find the top ${maxResults} trending themes or discussions.`;

    const tools = [];
    if (this.config.enableXSearch) {
      tools.push({ type: 'x_search' });
    }
    if (this.config.enableWebSearch) {
      tools.push({ type: 'web_search' });
    }

    const response = await fetch(`${this.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.config.apiKey}`,
      },
      body: JSON.stringify({
        model: this.config.model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
        tools: tools.length > 0 ? tools : undefined,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`xAI API error: ${response.status} - ${error}`);
    }

    const data = await response.json();
    const content = data.choices[0]?.message?.content || '';

    // Parse the response into structured format
    // This is a simplified parser - could be enhanced with more structured prompts
    return {
      query,
      trends: this.parseTopics(content),
      analysis: content,
      timestamp: new Date(),
    };
  }

  /**
   * Get financial trends specifically
   */
  async getFinancialTrends(): Promise<TrendAnalysis> {
    return this.analyzeTrends('stocks investing finance markets trading', {
      maxResults: 15,
      timeframe: 'today',
      sentiment: true,
    });
  }

  /**
   * Get trends relevant to financial advisors
   */
  async getAdvisorTrends(): Promise<TrendAnalysis> {
    return this.analyzeTrends('financial advisor wealth management retirement planning 401k', {
      maxResults: 10,
      timeframe: 'this_week',
      sentiment: true,
    });
  }

  /**
   * Search for specific topic mentions
   */
  async searchTopic(topic: string): Promise<TrendAnalysis> {
    return this.analyzeTrends(topic, {
      maxResults: 20,
      timeframe: 'recent',
      sentiment: true,
    });
  }

  /**
   * Simple topic extraction from analysis text
   */
  private parseTopics(content: string): Array<{ topic: string; summary: string; sentiment?: 'positive' | 'negative' | 'neutral' | 'mixed' }> {
    // This is a basic parser - the AI response is already well-formatted
    // For production, you'd want more structured output via function calling
    const lines = content.split('\n').filter(l => l.trim());
    const topics: Array<{ topic: string; summary: string }> = [];
    
    let currentTopic = '';
    for (const line of lines) {
      // Look for numbered items or bullet points
      if (/^\d+\.|^[-*•]/.test(line.trim())) {
        if (currentTopic) {
          topics.push({ topic: currentTopic, summary: '' });
        }
        currentTopic = line.replace(/^\d+\.|^[-*•]/, '').trim();
      }
    }
    if (currentTopic) {
      topics.push({ topic: currentTopic, summary: '' });
    }

    return topics.slice(0, 10);
  }
}

// Export for use
export { XAITrendsClient, XAIConfig, TrendAnalysis };

// CLI usage
if (require.main === module) {
  const client = new XAITrendsClient();
  
  console.log('🔍 Analyzing X trends...\n');
  
  client.getFinancialTrends()
    .then(result => {
      console.log('📊 Financial Trends Analysis:');
      console.log('=' .repeat(50));
      console.log(result.analysis);
      console.log('\n⏰ Generated:', result.timestamp.toISOString());
    })
    .catch(err => {
      console.error('Error:', err.message);
      process.exit(1);
    });
}
