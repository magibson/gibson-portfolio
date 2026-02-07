import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { callGemini } from "@/lib/gemini";

const SYSTEM_PROMPT = `You are an expert LinkedIn content editor. You help refine and improve LinkedIn posts based on user feedback.

Your edits:
- Maintain the original voice and style
- Make targeted improvements based on the user's request
- Keep the post authentic and engaging
- Preserve the core message unless asked to change it

Return ONLY the revised post content, no explanations or markdown formatting.`;

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const userId = (session.user as any).id;
    const { id } = await params;
    const body = await request.json();
    const { message } = body;

    if (!message) {
      return NextResponse.json({ error: "Message is required" }, { status: 400 });
    }

    // Verify the post belongs to the user
    const post = await prisma.post.findFirst({
      where: { id, userId },
    });

    if (!post) {
      return NextResponse.json({ error: "Post not found" }, { status: 404 });
    }

    const userPrompt = `Current LinkedIn post:
---
${post.content}
---

User feedback/request: ${message}

Please revise the post based on the user's feedback. Return only the revised post content.`;

    const refinedContent = await callGemini(
      [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: userPrompt },
      ],
      { temperature: 0.7, maxRetries: 3 }
    );

    return NextResponse.json({
      refinedContent,
      originalContent: post.content,
    });
  } catch (error: any) {
    console.error("Refine error:", error);
    const isRateLimit = error.message?.includes("429");
    return NextResponse.json(
      { error: isRateLimit ? "AI is busy — try again in a few seconds" : "Failed to refine post" },
      { status: isRateLimit ? 429 : 500 }
    );
  }
}
