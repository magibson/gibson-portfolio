import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import type { Post } from "@prisma/client";
import {
  generateDigestEmailHtml,
  generateSinglePostEmailHtml,
  type PostForEmail,
  type DigestEmailOptions,
  type SinglePostEmailOptions,
} from "@/lib/email";

/**
 * Preview email templates without sending
 * GET /api/email/preview?type=digest&batchId=xxx
 * GET /api/email/preview?type=single&postId=xxx
 */
export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const userId = (session.user as any).id;
    const { searchParams } = new URL(request.url);
    const type = searchParams.get("type") || "digest";
    const batchId = searchParams.get("batchId");
    const postId = searchParams.get("postId");
    const baseUrl = searchParams.get("baseUrl") || "";

    // Get user info
    const user = await prisma.user.findUnique({
      where: { id: userId },
      select: { firstName: true, email: true },
    });

    if (type === "single" && postId) {
      // Preview single post email
      const post = await prisma.post.findFirst({
        where: { id: postId, userId },
      });

      if (!post) {
        return NextResponse.json({ error: "Post not found" }, { status: 404 });
      }

      const html = generateSinglePostEmailHtml({
        userName: user?.firstName || user?.email?.split("@")[0] || "there",
        post: {
          id: post.id,
          topic: post.topic,
          content: post.content,
          tone: post.tone,
          contentType: post.contentType,
        },
        baseUrl,
      });

      return new NextResponse(html, {
        headers: { "Content-Type": "text/html" },
      });
    }

    // Preview digest email
    let posts;
    if (batchId) {
      posts = await prisma.post.findMany({
        where: { userId, batchId },
        orderBy: { createdAt: "desc" },
      });
    } else {
      // Use recent posts or sample posts
      posts = await prisma.post.findMany({
        where: { userId },
        orderBy: { createdAt: "desc" },
        take: 5,
      });
    }

    // If no posts exist, create sample data for preview
    const postsForEmail: PostForEmail[] =
      posts.length > 0
        ? posts.map((post: Post) => ({
            id: post.id,
            topic: post.topic,
            content: post.content,
            tone: post.tone,
            contentType: post.contentType,
          }))
        : [
            {
              id: "sample-1",
              topic: "Building Trust Through Transparency",
              content: `The moment a client says "I trust you" is when real financial planning begins.

Last week, a client asked me to explain our fee structure in detail. Instead of giving a quick overview, I pulled up a spreadsheet and walked through every single line item.

Her response? "No one has ever done that before."

Here's what I've learned: Transparency isn't about sharing information. It's about creating an environment where questions are welcomed, not feared.

Three ways to build trust through transparency:

1. Proactively share what others hide
2. Admit when you don't know something
3. Follow up even when there's nothing to report

The best client relationships aren't built on performance charts. They're built on honest conversations.

What's one way you demonstrate transparency with your clients?`,
              tone: "professional",
              contentType: "post",
            },
            {
              id: "sample-2",
              topic: "The Power of Long-term Planning",
              content: `I had a conversation yesterday that reminded me why I do this work.

A client I've worked with for 15 years called to thank me. Not for investment returns. Not for tax savings.

For being there when her husband passed away last year.

"You knew exactly what to do," she said. "You knew what documents we needed, what calls to make, what could wait."

That's the power of long-term planning. It's not about spreadsheets and projections.

It's about being the person who can step in when life gets hard.

This is why I believe in building relationships, not just portfolios.

Who are you building relationships with today?`,
              tone: "storytelling",
              contentType: "post",
            },
            {
              id: "sample-3",
              topic: "Continuous Learning in Financial Services",
              content: `Hot take: The advisors who stop learning are the ones who become irrelevant.

The market changes. Tax laws change. Client needs change.

Yesterday I spent 2 hours on a webinar about succession planning for business owners. Was it the most exciting way to spend a Tuesday afternoon? Maybe not.

But when my client asks about selling their business next quarter, I'll be ready.

The best advisors I know:
• Read industry publications daily
• Attend conferences (and actually take notes)
• Learn from their clients as much as they teach

Your credentials got you in the door. Your curiosity keeps you there.

What are you learning this week?`,
              tone: "thought-leader",
              contentType: "post",
            },
          ];

    const html = generateDigestEmailHtml({
      userName: user?.firstName || user?.email?.split("@")[0] || "there",
      posts: postsForEmail,
      batchId: batchId || undefined,
      baseUrl,
    });

    return new NextResponse(html, {
      headers: { "Content-Type": "text/html" },
    });
  } catch (error) {
    console.error("Email preview error:", error);
    return NextResponse.json(
      { error: "Failed to generate preview" },
      { status: 500 }
    );
  }
}
