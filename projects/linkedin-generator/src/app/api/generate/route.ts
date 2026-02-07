import { NextRequest, NextResponse } from "next/server";
import { articlesToPromptContext, CuratedArticle } from "@/lib/curation";

const SYSTEM_PROMPT = `You are an expert LinkedIn content creator. You write engaging, authentic posts that resonate with professional audiences.

Your posts:
- Start with a strong hook that stops the scroll
- Use short paragraphs and line breaks for readability
- Include relevant insights and value
- End with a call to action or thought-provoking question
- Feel genuine, not salesy or generic
- Use appropriate emojis sparingly (1-3 max)

Never use hashtags unless specifically asked. Focus on substance over fluff.`;

const getToneInstructions = (tone: string) => {
  switch (tone) {
    case "professional":
      return "Write in a polished, business-focused tone. Be clear, confident, and credible.";
    case "thought-leader":
      return "Write with authority and insight. Share a unique perspective or contrarian take. Position the author as an expert.";
    case "storytelling":
      return "Use a personal narrative style. Start with a specific moment or experience. Make it relatable and emotionally engaging.";
    case "casual":
      return "Write in a friendly, conversational tone. Be approachable and authentic. Like talking to a colleague over coffee.";
    default:
      return "";
  }
};

const getContentTypeInstructions = (contentType: string) => {
  switch (contentType) {
    case "post":
      return "Write a complete LinkedIn post (150-300 words). Include a hook, body, and conclusion.";
    case "hook":
      return "Write just the opening hook (1-2 sentences). Make it impossible to scroll past. Give 3-5 different options.";
    case "carousel-outline":
      return "Create a carousel outline with 6-10 slides. Format: Slide 1: [Title/Hook], Slide 2: [Point], etc. Keep each slide concise (1-2 sentences max).";
    default:
      return "";
  }
};

export async function POST(request: NextRequest) {
  try {
    const { topic, tone, contentType, writingStyle, postLength, curatedArticles } = await request.json();

    if (!topic) {
      return NextResponse.json({ error: "Topic is required" }, { status: 400 });
    }

    // Build article context if provided
    let articleContext = "";
    if (curatedArticles && Array.isArray(curatedArticles) && curatedArticles.length > 0) {
      articleContext = articlesToPromptContext(curatedArticles as CuratedArticle[]);
    }

    const apiKey = process.env.GEMINI_API_KEY;
    
    if (!apiKey) {
      return NextResponse.json(
        { error: "Gemini API key not configured" },
        { status: 500 }
      );
    }

    const getLengthInstructions = (length: string) => {
      switch (length) {
        case "short": return "Keep it concise, around 100 words.";
        case "long": return "Make it comprehensive, around 300 words.";
        default: return "Aim for around 200 words.";
      }
    };

    const styleNote = writingStyle 
      ? `\n\nMatch this writing style:\n${writingStyle}`
      : "";

    const articleNote = articleContext
      ? `\n\n${articleContext}\n\nUse insights from these articles to inform your post. You may reference specific articles naturally (e.g., "A recent article from [source] highlighted...") when it adds value.`
      : "";

    const userPrompt = `${getToneInstructions(tone)}

${getContentTypeInstructions(contentType)}

${getLengthInstructions(postLength)}

Target audience: New York Life financial advisors
${styleNote}${articleNote}

Topic: ${topic}`;

    // Using Google's OpenAI-compatible endpoint
    const response = await fetch("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: "gemini-2.0-flash",
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: userPrompt },
        ],
        temperature: 0.8,
        max_tokens: 1000,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      console.error("Gemini API error:", error);
      return NextResponse.json(
        { error: "Failed to generate content" },
        { status: 500 }
      );
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content || "No content generated";

    return NextResponse.json({ content });
  } catch (error) {
    console.error("Generation error:", error);
    return NextResponse.json(
      { error: "Failed to generate content" },
      { status: 500 }
    );
  }
}
