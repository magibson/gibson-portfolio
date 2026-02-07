import Parser from "rss-parser";
import * as cheerio from "cheerio";
import { AudienceType, AUDIENCES, getTopicsForAudience } from "./types";

const parser = new Parser({
  timeout: 10000,
  headers: {
    "User-Agent": "LinkedIn-Generator/1.0 (RSS Reader)",
  },
});

export interface CuratedArticle {
  title: string;
  url: string;
  summary: string;
  imageUrl: string | null;
  publishedAt: string | null;
  source: string;
  matchedTopics: string[];
  relevanceScore: number;
}

export interface CurationResult {
  articles: CuratedArticle[];
  errors: { source: string; error: string }[];
  fetchedAt: string;
}

// Common RSS feed paths to try for a website
const RSS_PATHS = [
  "/feed",
  "/rss",
  "/feed.xml",
  "/rss.xml",
  "/atom.xml",
  "/feed/",
  "/rss/",
  "/blog/feed",
  "/blog/rss",
  "/news/feed",
];

// Known RSS feeds for common finance/news sites
const KNOWN_RSS_FEEDS: Record<string, string> = {
  "investopedia.com": "https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_headline",
  "bloomberg.com": "https://www.bloomberg.com/feed/podcast/etf-iq.xml",
  "cnbc.com": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
  "marketwatch.com": "https://feeds.marketwatch.com/marketwatch/topstories",
  "fool.com": "https://www.fool.com/feeds/index.aspx",
  "kiplinger.com": "https://www.kiplinger.com/rss.xml",
  "nerdwallet.com": "https://www.nerdwallet.com/blog/feed/",
  "forbes.com": "https://www.forbes.com/money/feed/",
};

// Backup financial news sources for fallback
export const BACKUP_SOURCES = [
  "https://www.investopedia.com",
  "https://www.kiplinger.com",
  "https://www.cnbc.com/personal-finance/",
  "https://www.nerdwallet.com",
];

/**
 * Fetch og:image meta tag from an article URL
 */
async function fetchOgImage(url: string): Promise<string | null> {
  try {
    const response = await fetch(url, {
      headers: { "User-Agent": "LinkedIn-Generator/1.0" },
      signal: AbortSignal.timeout(8000),
    });

    if (!response.ok) return null;

    const html = await response.text();
    const $ = cheerio.load(html);

    // Try various image meta tags
    const ogImage = $('meta[property="og:image"]').attr("content") ||
      $('meta[name="og:image"]').attr("content") ||
      $('meta[property="twitter:image"]').attr("content") ||
      $('meta[name="twitter:image"]').attr("content") ||
      $('meta[property="twitter:image:src"]').attr("content");

    if (ogImage) {
      // Make URL absolute if relative
      if (ogImage.startsWith("//")) {
        return "https:" + ogImage;
      } else if (ogImage.startsWith("/")) {
        return new URL(ogImage, url).toString();
      }
      return ogImage;
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Try to discover RSS feed URL for a website
 */
async function discoverRssFeed(baseUrl: string): Promise<string | null> {
  // Check known feeds first
  const domain = new URL(baseUrl).hostname.replace("www.", "");
  if (KNOWN_RSS_FEEDS[domain]) {
    return KNOWN_RSS_FEEDS[domain];
  }

  // Try common paths
  for (const path of RSS_PATHS) {
    const feedUrl = new URL(path, baseUrl).toString();
    try {
      const response = await fetch(feedUrl, {
        method: "HEAD",
        headers: { "User-Agent": "LinkedIn-Generator/1.0" },
        signal: AbortSignal.timeout(5000),
      });
      if (response.ok) {
        const contentType = response.headers.get("content-type") || "";
        if (
          contentType.includes("xml") ||
          contentType.includes("rss") ||
          contentType.includes("atom")
        ) {
          return feedUrl;
        }
      }
    } catch {
      continue;
    }
  }

  // Try to find RSS link in page HTML
  try {
    const response = await fetch(baseUrl, {
      headers: { "User-Agent": "LinkedIn-Generator/1.0" },
      signal: AbortSignal.timeout(10000),
    });
    const html = await response.text();
    const $ = cheerio.load(html);

    // Look for RSS link in head
    const rssLink = $('link[type="application/rss+xml"]').attr("href") ||
      $('link[type="application/atom+xml"]').attr("href");

    if (rssLink) {
      return new URL(rssLink, baseUrl).toString();
    }
  } catch {
    // Ignore errors
  }

  return null;
}

/**
 * Fetch articles from an RSS feed
 */
async function fetchRssFeed(feedUrl: string): Promise<CuratedArticle[]> {
  const feed = await parser.parseURL(feedUrl);
  const articles: CuratedArticle[] = [];

  for (const item of feed.items || []) {
    const publishedAt = item.pubDate || item.isoDate || null;

    // Extract summary - try different fields
    let summary = item.contentSnippet || item.content || item.description || "";
    
    // Clean up HTML and limit length
    const $summary = cheerio.load(summary);
    summary = $summary.root().text().trim();
    if (summary.length > 300) {
      summary = summary.substring(0, 297) + "...";
    }

    // Try to get image from RSS enclosure or media content
    let imageUrl: string | null = null;
    if ((item as any).enclosure?.url) {
      imageUrl = (item as any).enclosure.url;
    } else if ((item as any)["media:content"]?.url) {
      imageUrl = (item as any)["media:content"].url;
    } else if ((item as any)["media:thumbnail"]?.url) {
      imageUrl = (item as any)["media:thumbnail"].url;
    }

    articles.push({
      title: item.title || "Untitled",
      url: item.link || "",
      summary,
      imageUrl,
      publishedAt,
      source: feed.title || new URL(feedUrl).hostname,
      matchedTopics: [],
      relevanceScore: 0,
    });
  }

  return articles;
}

/**
 * Scrape articles from a website when RSS is not available
 */
async function scrapeWebsite(url: string): Promise<CuratedArticle[]> {
  const response = await fetch(url, {
    headers: { "User-Agent": "LinkedIn-Generator/1.0" },
    signal: AbortSignal.timeout(15000),
  });

  const html = await response.text();
  const $ = cheerio.load(html);
  const articles: CuratedArticle[] = [];
  const hostname = new URL(url).hostname;

  // Common article selectors
  const articleSelectors = [
    "article",
    ".article",
    ".post",
    ".entry",
    '[class*="article"]',
    '[class*="post"]',
    ".story",
    ".news-item",
    ".blog-post",
  ];

  // Find article containers
  let $articles = $("__no_match__"); // Initialize with empty selection
  for (const selector of articleSelectors) {
    const found = $(selector);
    if (found.length > 0) {
      $articles = found;
      break;
    }
  }

  // If no articles found, try finding links with headlines
  if ($articles.length === 0) {
    // Look for headline links
    $("a").each((_, el) => {
      const $el = $(el);
      const href = $el.attr("href");
      const text = $el.text().trim();

      // Filter to likely article links
      if (
        href &&
        text.length > 30 &&
        text.length < 200 &&
        !href.includes("#") &&
        (href.includes("/article") ||
          href.includes("/news") ||
          href.includes("/blog") ||
          href.includes("/post") ||
          /\/\d{4}\//.test(href))
      ) {
        articles.push({
          title: text,
          url: new URL(href, url).toString(),
          summary: "",
          imageUrl: null,
          publishedAt: null,
          source: hostname,
          matchedTopics: [],
          relevanceScore: 0,
        });
      }
    });
  } else {
    $articles.slice(0, 20).each((_, el) => {
      const $article = $(el);

      // Find title
      const $title =
        $article.find("h1, h2, h3, h4, .title, .headline").first() ||
        $article.find("a").first();
      const title = $title.text().trim();

      // Find link
      let link = $article.find("a").first().attr("href") || "";
      if (link && !link.startsWith("http")) {
        link = new URL(link, url).toString();
      }

      // Find summary/description
      const summary =
        $article.find("p, .excerpt, .summary, .description").first().text().trim() ||
        "";

      // Find date
      const dateText =
        $article.find("time, .date, .published").first().attr("datetime") ||
        $article.find("time, .date, .published").first().text();

      // Find image
      const imgSrc = $article.find("img").first().attr("src") || null;
      let imageUrl: string | null = null;
      if (imgSrc) {
        imageUrl = imgSrc.startsWith("http") ? imgSrc : new URL(imgSrc, url).toString();
      }

      if (title && link) {
        articles.push({
          title,
          url: link,
          summary: summary.substring(0, 300),
          imageUrl,
          publishedAt: dateText || null,
          source: hostname,
          matchedTopics: [],
          relevanceScore: 0,
        });
      }
    });
  }

  // Deduplicate by URL
  const seen = new Set<string>();
  return articles.filter((a) => {
    if (seen.has(a.url)) return false;
    seen.add(a.url);
    return true;
  });
}

/**
 * Check if an article was published within the last N days
 */
function isWithinDays(dateStr: string | null, days: number): boolean {
  if (!dateStr) return true; // Include if no date (be inclusive)

  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return true;

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);

    return date >= cutoff;
  } catch {
    return true;
  }
}

/**
 * Calculate relevance score based on topic matching
 */
function calculateRelevance(
  article: CuratedArticle,
  topics: string[]
): { matchedTopics: string[]; score: number } {
  const matchedTopics: string[] = [];
  const textToSearch = `${article.title} ${article.summary}`.toLowerCase();

  for (const topic of topics) {
    // Split topic into keywords and check for matches
    const keywords = topic.toLowerCase().split(/\s+/);
    const matchCount = keywords.filter((kw) =>
      textToSearch.includes(kw)
    ).length;

    // Consider it a match if more than half the keywords are present
    if (matchCount >= Math.ceil(keywords.length / 2)) {
      matchedTopics.push(topic);
    }
  }

  // Score based on matches and title vs summary weighting
  let score = matchedTopics.length * 10;

  // Bonus for title matches (more relevant)
  const titleLower = article.title.toLowerCase();
  for (const topic of matchedTopics) {
    const keywords = topic.toLowerCase().split(/\s+/);
    if (keywords.some((kw) => titleLower.includes(kw))) {
      score += 5;
    }
  }

  return { matchedTopics, score };
}

/**
 * Fetch articles from a single source (RSS or scraping)
 */
async function fetchFromSource(url: string): Promise<CuratedArticle[]> {
  // Normalize URL
  if (!url.startsWith("http")) {
    url = "https://" + url;
  }

  // Try RSS first
  const rssFeedUrl = await discoverRssFeed(url);
  if (rssFeedUrl) {
    try {
      return await fetchRssFeed(rssFeedUrl);
    } catch (e) {
      console.warn(`RSS failed for ${url}, falling back to scraping:`, e);
    }
  }

  // Fall back to scraping
  return await scrapeWebsite(url);
}

/**
 * Enrich articles with og:image if they don't have images
 * Only fetches for the top N articles to avoid too many requests
 */
async function enrichArticlesWithImages(
  articles: CuratedArticle[],
  maxToEnrich: number = 10
): Promise<CuratedArticle[]> {
  const articlesToEnrich = articles.slice(0, maxToEnrich).filter(a => !a.imageUrl);
  
  if (articlesToEnrich.length === 0) return articles;

  // Fetch images in parallel with concurrency limit
  const enrichPromises = articlesToEnrich.map(async (article) => {
    const imageUrl = await fetchOgImage(article.url);
    return { url: article.url, imageUrl };
  });

  const results = await Promise.all(enrichPromises);
  const imageMap = new Map(results.map(r => [r.url, r.imageUrl]));

  return articles.map(article => ({
    ...article,
    imageUrl: article.imageUrl || imageMap.get(article.url) || null,
  }));
}

/**
 * Main function: Curate articles from source websites
 */
export async function curateArticles(
  sourceWebsites: string[],
  audience: AudienceType,
  customTopics: string[] = [],
  options: {
    maxDays?: number;
    maxArticlesPerSource?: number;
    maxTotalArticles?: number;
    enrichImages?: boolean;
  } = {}
): Promise<CurationResult> {
  const {
    maxDays = 7,
    maxArticlesPerSource = 10,
    maxTotalArticles = 30,
    enrichImages = true,
  } = options;

  const topics = getTopicsForAudience(audience, customTopics);
  const allArticles: CuratedArticle[] = [];
  const errors: { source: string; error: string }[] = [];

  // Fetch from each source in parallel (with concurrency limit)
  const promises = sourceWebsites.map(async (source) => {
    try {
      const articles = await fetchFromSource(source);

      // Filter by date
      const recentArticles = articles.filter((a) =>
        isWithinDays(a.publishedAt, maxDays)
      );

      // Calculate relevance for each article
      const scoredArticles = recentArticles.map((article) => {
        const { matchedTopics, score } = calculateRelevance(article, topics);
        return {
          ...article,
          matchedTopics,
          relevanceScore: score,
        };
      });

      // Sort by relevance and take top N
      // Include all articles, but prioritize ones with topic matches
      const topArticles = scoredArticles
        .sort((a, b) => b.relevanceScore - a.relevanceScore)
        .slice(0, maxArticlesPerSource);

      return { source, articles: topArticles, error: null };
    } catch (e) {
      const error = e instanceof Error ? e.message : String(e);
      return { source, articles: [], error };
    }
  });

  const results = await Promise.all(promises);

  for (const result of results) {
    if (result.error) {
      errors.push({ source: result.source, error: result.error });
    } else {
      allArticles.push(...result.articles);
    }
  }

  // Deduplicate first
  const seenUrls = new Set<string>();
  const deduplicatedArticles = allArticles
    .filter((a) => {
      if (seenUrls.has(a.url)) return false;
      seenUrls.add(a.url);
      return true;
    });

  // Smart selection: Pick best articles with diversity bonus
  // Uses diminishing returns for sources already selected
  const sourceUsageCount = new Map<string, number>();
  let uniqueArticles: CuratedArticle[] = [];
  const remainingArticles = [...deduplicatedArticles];

  while (uniqueArticles.length < maxTotalArticles && remainingArticles.length > 0) {
    // Calculate adjusted score for each remaining article
    // Penalize sources we've already used (diminishing returns)
    let bestIndex = 0;
    let bestAdjustedScore = -1;

    for (let i = 0; i < remainingArticles.length; i++) {
      const article = remainingArticles[i];
      const sourceKey = article.source.toLowerCase();
      const usageCount = sourceUsageCount.get(sourceKey) || 0;
      
      // Diversity penalty: each additional article from same source gets 40% less weight
      const diversityMultiplier = Math.pow(0.6, usageCount);
      const adjustedScore = article.relevanceScore * diversityMultiplier;
      
      // Bonus for sources not yet used (encourage at least one from each)
      const firstUseBonus = usageCount === 0 ? 5 : 0;
      const finalScore = adjustedScore + firstUseBonus;

      if (finalScore > bestAdjustedScore) {
        bestAdjustedScore = finalScore;
        bestIndex = i;
      }
    }

    // Select the best article
    const selected = remainingArticles.splice(bestIndex, 1)[0];
    uniqueArticles.push(selected);
    
    // Update source usage count
    const sourceKey = selected.source.toLowerCase();
    sourceUsageCount.set(sourceKey, (sourceUsageCount.get(sourceKey) || 0) + 1);
  }

  uniqueArticles = uniqueArticles.slice(0, maxTotalArticles);

  // Enrich top articles with og:image if needed
  if (enrichImages) {
    uniqueArticles = await enrichArticlesWithImages(uniqueArticles, Math.min(15, maxTotalArticles));
  }

  return {
    articles: uniqueArticles,
    errors,
    fetchedAt: new Date().toISOString(),
  };
}

/**
 * Generate a prompt context from curated articles
 */
export function articlesToPromptContext(articles: CuratedArticle[]): string {
  if (articles.length === 0) return "";

  const contextLines = articles.map((article, i) => {
    const topics = article.matchedTopics.length > 0
      ? `Topics: ${article.matchedTopics.join(", ")}`
      : "";

    return `[Article ${i + 1}]
Title: ${article.title}
Source: ${article.source}
URL: ${article.url}
${article.summary ? `Summary: ${article.summary}` : ""}
${topics}`.trim();
  });

  return `--- CURATED ARTICLES FOR REFERENCE ---
Use these recent articles as inspiration and context. Reference them naturally when relevant.

${contextLines.join("\n\n")}

--- END CURATED ARTICLES ---`;
}

/**
 * Get topic suggestions based on curated articles
 */
export function suggestTopicsFromArticles(articles: CuratedArticle[]): string[] {
  const topicCounts = new Map<string, number>();

  for (const article of articles) {
    for (const topic of article.matchedTopics) {
      topicCounts.set(topic, (topicCounts.get(topic) || 0) + 1);
    }
  }

  // Sort by frequency and return top topics
  return Array.from(topicCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([topic]) => topic);
}
