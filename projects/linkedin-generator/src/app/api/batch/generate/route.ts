import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { sendDigestEmail, isEmailConfigured, PostForEmail } from "@/lib/email";
import { curateArticles, articlesToPromptContext, CuratedArticle, BACKUP_SOURCES } from "@/lib/curation";
import { AudienceType } from "@/lib/types";
import { callGemini } from "@/lib/gemini";

const SYSTEM_PROMPT = `You are a financial advisor sharing valuable articles with your LinkedIn network. Your posts share interesting articles and add your professional perspective.

Your posts should:
- Open with a hook about the article's key insight or why it matters
- Briefly summarize what the article covers (1-2 sentences)
- Add YOUR professional take or perspective on the topic
- End with a question to spark discussion
- Feel like genuine sharing, not promotion
- Use appropriate emojis sparingly (1-2 max)

IMPORTANT: 
- The article link will be added separately, so DON'T include the URL in your text
- Focus on providing value and your unique perspective
- Never use hashtags
- Write as someone sharing something helpful they found, not selling`;

const getToneInstructions = (tone: string) => {
  switch (tone) {
    case "professional":
      return "Write in a polished, business-focused tone. Be clear, confident, and credible.";
    case "thought-leader":
      return "Write with authority and insight. Share a unique perspective or contrarian take.";
    case "storytelling":
      return "Use a personal narrative style. Make it relatable and emotionally engaging.";
    case "casual":
      return "Write in a friendly, conversational tone. Be approachable and authentic.";
    default:
      return "";
  }
};

const getLengthInstructions = (length: string) => {
  switch (length) {
    case "short":
      return "Keep it concise, around 100 words.";
    case "long":
      return "Make it comprehensive, around 300 words.";
    default:
      return "Aim for around 200 words.";
  }
};

// Topics for auto-generation when no specific topic is provided
const AUTO_TOPICS = [
  "Building trust with clients through transparency",
  "The power of long-term financial planning",
  "Lessons learned from helping families with life insurance",
  "Why protection planning matters more than ever",
  "The difference between selling and serving in financial services",
  "How to have difficult conversations about money",
  "Building a referral-based practice",
  "The importance of continuous learning in financial services",
  "Balancing work and family as a financial professional",
  "What clients really want from their advisor",
];

const TONES = ["professional", "thought-leader", "storytelling", "casual"];

interface ArticleForPost {
  title: string;
  url: string;
  summary: string;
  source: string;
}

async function generateSinglePost(
  article: ArticleForPost,
  tone: string,
  postLength: string,
  writingStyle: string,
  aiInstructions: string
): Promise<{ topic: string; tone: string; content: string } | null> {
  const styleNote = writingStyle
    ? `\n\nMatch this writing style:\n${writingStyle}`
    : "";

  const instructionsNote = aiInstructions
    ? `\n\nIMPORTANT - Follow these custom instructions:\n${aiInstructions}`
    : "";

  const articleContext = `
ARTICLE TO SHARE:
Title: ${article.title}
Source: ${article.source}
Summary: ${article.summary}

Write a LinkedIn post sharing this article with your professional network. Your post should:
1. Hook the reader with why this article matters
2. Briefly mention what the article covers
3. Add your perspective as a financial professional
4. Ask a question to encourage comments

Remember: The article link will be added after your text automatically. Do NOT write the URL.`;

  const userPrompt = `${getToneInstructions(tone)}

${getLengthInstructions(postLength)}
${styleNote}
${instructionsNote}

${articleContext}`;

  try {
    const content = await callGemini(
      [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: userPrompt },
      ],
      { temperature: 0.8, maxRetries: 3, baseDelayMs: 3000 }
    );

    return { topic: article.title, tone, content };
  } catch (err) {
    console.error("Generation error:", err);
    return null;
  }
}

const WEEKLY_LIMIT = 20; // Posts per user per week

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const userId = (session.user as any).id;
    const body = await request.json();
    
    // Check weekly usage limit
    const now = new Date();
    const dayOfWeek = now.getDay();
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - dayOfWeek);
    startOfWeek.setHours(0, 0, 0, 0);

    const postsThisWeek = await prisma.post.count({
      where: {
        userId,
        createdAt: {
          gte: startOfWeek,
        },
      },
    });

    const requestedCount = body.count || 5;
    const remaining = WEEKLY_LIMIT - postsThisWeek;

    if (remaining <= 0) {
      return NextResponse.json(
        { error: "Weekly limit reached. You can generate more posts next week." },
        { status: 429 }
      );
    }

    if (requestedCount > remaining) {
      return NextResponse.json(
        { error: `You can only generate ${remaining} more posts this week. Please reduce the count.` },
        { status: 429 }
      );
    }
    const { 
      topics, // Optional array of specific topics
      count, // Optional override for number of posts
      sendEmail = true, // Whether to send email after generation
      baseUrl = "", // Base URL for email links
      useCuratedArticles = true, // Whether to fetch and use curated articles
      curatedArticles, // Optional pre-fetched articles to use
    } = body;

    // Get user settings
    const settings = await prisma.userSettings.findUnique({
      where: { userId },
    });

    if (!settings) {
      return NextResponse.json(
        { error: "Please configure your settings first" },
        { status: 400 }
      );
    }

    // Get writing style from examples
    const writingExamples = await prisma.writingExample.findMany({
      where: { userId },
      orderBy: { createdAt: "desc" },
    });
    const writingStyle = writingExamples.map((e: { content: string }) => e.content).join("\n\n---\n\n");

    const postsToGenerate = count || settings.postsPerBatch;
    const postLength = settings.postLength;
    const sourceWebsites = JSON.parse(settings.sourceWebsites || "[]") as string[];
    const customTopics = JSON.parse(settings.customTopics || "[]") as string[];
    const audience = (settings.audience || "young-professionals") as AudienceType;
    const aiInstructions = settings.aiInstructions || "";

    // Fetch curated articles from source websites
    let fetchedArticles: CuratedArticle[] = [];
    
    if (useCuratedArticles && (curatedArticles || sourceWebsites.length > 0)) {
      try {
        if (curatedArticles && Array.isArray(curatedArticles)) {
          // Use pre-fetched articles
          fetchedArticles = curatedArticles;
        } else if (sourceWebsites.length > 0) {
          // Fetch fresh articles from user's sources
          const curationResult = await curateArticles(sourceWebsites, audience, customTopics, {
            maxDays: 14, // 2 weeks for more options
            maxTotalArticles: postsToGenerate + 5, // Fetch a few extra
            maxArticlesPerSource: 10,
          });
          fetchedArticles = curationResult.articles;
        }

        // If we don't have enough articles, fetch from backup sources
        if (fetchedArticles.length < postsToGenerate) {
          console.log(`Only got ${fetchedArticles.length} articles, need ${postsToGenerate}. Fetching from backup sources...`);
          
          // Filter out backup sources the user already has
          const userDomains = new Set(sourceWebsites.map(url => {
            try {
              return new URL(url.startsWith("http") ? url : "https://" + url).hostname.replace("www.", "");
            } catch {
              return url;
            }
          }));
          
          const backupSourcesToUse = BACKUP_SOURCES.filter(url => {
            const domain = new URL(url).hostname.replace("www.", "");
            return !userDomains.has(domain);
          });
          
          if (backupSourcesToUse.length > 0) {
            const needed = postsToGenerate - fetchedArticles.length;
            const backupResult = await curateArticles(backupSourcesToUse, audience, customTopics, {
              maxDays: 14,
              maxTotalArticles: needed + 3,
              maxArticlesPerSource: Math.ceil(needed / backupSourcesToUse.length) + 2,
            });
            
            // Append backup articles (user's sources stay prioritized at top)
            const existingUrls = new Set(fetchedArticles.map(a => a.url));
            const newBackupArticles = backupResult.articles.filter(a => !existingUrls.has(a.url));
            fetchedArticles = [...fetchedArticles, ...newBackupArticles];
            
            console.log(`After backup sources: ${fetchedArticles.length} total articles`);
          }
        }
        
      } catch (e) {
        console.warn("Failed to fetch curated articles:", e);
        // Continue without articles
      }
    }

    // Create a batch record
    const batch = await prisma.batch.create({
      data: {
        userId,
        scheduledFor: new Date(),
        status: "generating",
      },
    });

    // We need articles to generate posts about
    if (fetchedArticles.length === 0) {
      await prisma.batch.update({
        where: { id: batch.id },
        data: { status: "complete" },
      });
      return NextResponse.json(
        { error: "No articles found from your source websites. Try adding more sources or adjusting your audience settings." },
        { status: 400 }
      );
    }

    // Generate posts - one per article
    const articlesToUse = fetchedArticles.slice(0, postsToGenerate);
    const generatedPosts: { topic: string; tone: string; content: string; sourceArticle: CuratedArticle }[] = [];
    
    for (let i = 0; i < articlesToUse.length; i++) {
      const article = articlesToUse[i];
      const tone = TONES[i % TONES.length]; // Rotate through tones
      
      const result = await generateSinglePost(
        {
          title: article.title,
          url: article.url,
          summary: article.summary,
          source: article.source,
        },
        tone,
        postLength,
        writingStyle,
        aiInstructions
      );
      
      if (result) {
        generatedPosts.push({
          ...result,
          sourceArticle: article,
        });
      }
    }

    if (generatedPosts.length === 0) {
      await prisma.batch.update({
        where: { id: batch.id },
        data: { status: "complete" },
      });
      return NextResponse.json(
        { error: "Failed to generate any posts" },
        { status: 500 }
      );
    }

    // Save posts to database (with source article info)
    // Append article URL to content so it's included when copying
    const savedPosts = await Promise.all(
      generatedPosts.map((post: { topic: string; tone: string; content: string; sourceArticle: CuratedArticle }) => {
        const contentWithLink = `${post.content}\n\n${post.sourceArticle.url}`;
        return prisma.post.create({
          data: {
            userId,
            batchId: batch.id,
            topic: post.topic,
            tone: post.tone,
            contentType: "post",
            content: contentWithLink,
            status: "draft",
            sourceArticleUrl: post.sourceArticle.url,
            sourceArticleTitle: post.sourceArticle.title,
            sourceArticleImage: post.sourceArticle.imageUrl,
            audience: audience,
          },
        });
      })
    );

    // Update batch status
    await prisma.batch.update({
      where: { id: batch.id },
      data: {
        status: "complete",
        generatedAt: new Date(),
      },
    });

    // Send email if configured and requested
    let emailResult = null;
    if (sendEmail && settings.emailAddress && isEmailConfigured()) {
      const user = await prisma.user.findUnique({
        where: { id: userId },
        select: { firstName: true, email: true },
      });

      const postsForEmail: PostForEmail[] = savedPosts.map((post: { id: string; topic: string; content: string; tone: string; contentType: string }) => ({
        id: post.id,
        topic: post.topic,
        content: post.content,
        tone: post.tone,
        contentType: post.contentType,
      }));

      emailResult = await sendDigestEmail({
        to: settings.emailAddress,
        userName: user?.firstName || user?.email?.split("@")[0] || "there",
        posts: postsForEmail,
        batchId: batch.id,
        baseUrl,
      });

      if (emailResult.success) {
        await prisma.batch.update({
          where: { id: batch.id },
          data: {
            sentAt: new Date(),
            status: "sent",
          },
        });
      }
    }

    return NextResponse.json({
      success: true,
      batch: {
        id: batch.id,
        status: emailResult?.success ? "sent" : "complete",
      },
      posts: savedPosts.map((p: { id: string; topic: string; tone: string; content: string }, i: number) => ({
        id: p.id,
        topic: p.topic,
        tone: p.tone,
        preview: p.content.substring(0, 100) + "...",
        sourceArticle: generatedPosts[i]?.sourceArticle || null,
      })),
      curation: {
        articlesUsed: fetchedArticles.length,
        sources: [...new Set(fetchedArticles.map(a => a.source))],
      },
      audience,
      email: emailResult
        ? {
            sent: emailResult.success,
            error: emailResult.error,
          }
        : {
            sent: false,
            reason: !settings.emailAddress
              ? "No email address configured"
              : !isEmailConfigured()
              ? "RESEND_API_KEY not set"
              : "Email not requested",
          },
    });
  } catch (error) {
    console.error("Batch generation error:", error);
    return NextResponse.json(
      { error: "Failed to generate batch" },
      { status: 500 }
    );
  }
}
