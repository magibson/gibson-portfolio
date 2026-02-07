/**
 * X Trends Demo
 * 
 * Shows how to use each of the trend monitoring clients.
 * Run with: npx ts-node examples/demo.ts
 */

import { ApifyTrendsClient } from '../clients/apify-trends';
import { XAITrendsClient } from '../clients/xai-trends';
import { RapidAPITrendsClient, WOEID } from '../clients/rapidapi-trends';

async function demoApify() {
  console.log('\n' + '='.repeat(60));
  console.log('📊 APIFY TRENDS DEMO (Cheapest Option)');
  console.log('='.repeat(60));
  
  try {
    const client = new ApifyTrendsClient();
    
    // Get US trends
    console.log('\n🇺🇸 Fetching US trends...');
    const usTrends = await client.getUSTrends();
    
    console.log(`\nTop 10 US Trends (${usTrends.scrapedAt.toLocaleString()}):`);
    for (const trend of usTrends.trends.slice(0, 10)) {
      console.log(`  ${trend.rank}. ${trend.name} - ${trend.tweetCount} tweets`);
    }
    
    // Filter for financial trends
    console.log('\n💰 Financial-related trends:');
    const financialTrends = await client.getFinancialTrends();
    if (financialTrends.length === 0) {
      console.log('  (No financial trends in top 50 right now)');
    } else {
      for (const trend of financialTrends.slice(0, 5)) {
        console.log(`  • ${trend.name} - ${trend.tweetCount} tweets`);
      }
    }
    
  } catch (error: any) {
    console.error('❌ Apify error:', error.message);
    console.log('   Make sure APIFY_TOKEN is set in config/apify.env');
  }
}

async function demoXAI() {
  console.log('\n' + '='.repeat(60));
  console.log('🤖 XAI GROK DEMO (AI-Powered Analysis)');
  console.log('='.repeat(60));
  
  try {
    const client = new XAITrendsClient();
    
    // Analyze financial trends with AI
    console.log('\n📈 Analyzing financial discussions on X...');
    const analysis = await client.getFinancialTrends();
    
    console.log('\nAI Analysis:');
    console.log('-'.repeat(40));
    console.log(analysis.analysis);
    console.log('-'.repeat(40));
    console.log(`Generated: ${analysis.timestamp.toLocaleString()}`);
    
  } catch (error: any) {
    console.error('❌ xAI error:', error.message);
    console.log('   Make sure XAI_API_KEY is set in config/xai.env');
  }
}

async function demoRapidAPI() {
  console.log('\n' + '='.repeat(60));
  console.log('⚡ RAPIDAPI TRENDS DEMO (Free Tier Available)');
  console.log('='.repeat(60));
  
  try {
    const client = new RapidAPITrendsClient();
    
    // Get US trends
    console.log('\n🇺🇸 Fetching US trends...');
    const usTrends = await client.getUSTrends();
    
    console.log(`\nTop 10 US Trends (${usTrends.fetchedAt.toLocaleString()}):`);
    for (const trend of usTrends.trends.slice(0, 10)) {
      console.log(`  ${trend.rank}. ${trend.name} - ${trend.tweetCount} tweets`);
    }
    
  } catch (error: any) {
    console.error('❌ RapidAPI error:', error.message);
    console.log('   Make sure RAPIDAPI_KEY is set in config/rapidapi.env');
  }
}

// Main entry point
async function main() {
  const args = process.argv.slice(2);
  
  console.log('🐦 X (Twitter) Trends Demo');
  console.log('Usage: npx ts-node demo.ts [apify|xai|rapidapi|all]');
  
  const mode = args[0] || 'all';
  
  switch (mode) {
    case 'apify':
      await demoApify();
      break;
    case 'xai':
      await demoXAI();
      break;
    case 'rapidapi':
      await demoRapidAPI();
      break;
    case 'all':
    default:
      await demoApify();
      await demoXAI();
      await demoRapidAPI();
      break;
  }
  
  console.log('\n✅ Demo complete!\n');
}

main().catch(console.error);
