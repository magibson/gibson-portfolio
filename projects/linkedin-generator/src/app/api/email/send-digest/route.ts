import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import {
  sendDigestEmail,
  isEmailConfigured,
  PostForEmail,
} from "@/lib/email";

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const userId = (session.user as any).id;
    const body = await request.json();
    const { batchId, postIds, baseUrl } = body;

    // Check if email is configured
    if (!isEmailConfigured()) {
      return NextResponse.json(
        { 
          error: "Email not configured", 
          message: "RESEND_API_KEY is not set. Add it to your environment to enable emails." 
        },
        { status: 503 }
      );
    }

    // Get user settings to find email address
    const settings = await prisma.userSettings.findUnique({
      where: { userId },
    });

    if (!settings?.emailAddress) {
      return NextResponse.json(
        { error: "No email address configured. Please add one in Settings." },
        { status: 400 }
      );
    }

    // Get posts to include in digest
    let posts;
    if (batchId) {
      // Get all posts from a specific batch
      posts = await prisma.post.findMany({
        where: {
          userId,
          batchId,
        },
        orderBy: { createdAt: "desc" },
      });
    } else if (postIds && Array.isArray(postIds)) {
      // Get specific posts by ID
      posts = await prisma.post.findMany({
        where: {
          userId,
          id: { in: postIds },
        },
        orderBy: { createdAt: "desc" },
      });
    } else {
      // Get recent draft posts (last 24 hours)
      const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
      posts = await prisma.post.findMany({
        where: {
          userId,
          status: "draft",
          createdAt: { gte: oneDayAgo },
        },
        orderBy: { createdAt: "desc" },
        take: 10,
      });
    }

    if (posts.length === 0) {
      return NextResponse.json(
        { error: "No posts found to send" },
        { status: 400 }
      );
    }

    // Get user name for email greeting
    const user = await prisma.user.findUnique({
      where: { id: userId },
      select: { firstName: true, email: true },
    });

    // Format posts for email
    const postsForEmail: PostForEmail[] = posts.map((post) => ({
      id: post.id,
      topic: post.topic,
      content: post.content,
      tone: post.tone,
      contentType: post.contentType,
    }));

    // Send the email
    const result = await sendDigestEmail({
      to: settings.emailAddress,
      userName: user?.firstName || user?.email?.split("@")[0] || "there",
      posts: postsForEmail,
      batchId,
      baseUrl: baseUrl || "",
    });

    if (!result.success) {
      return NextResponse.json(
        { error: result.error || "Failed to send email" },
        { status: 500 }
      );
    }

    // If this was a batch, update its status
    if (batchId) {
      await prisma.batch.update({
        where: { id: batchId },
        data: {
          sentAt: new Date(),
          status: "sent",
        },
      });
    }

    return NextResponse.json({
      success: true,
      messageId: result.messageId,
      postsCount: posts.length,
      sentTo: settings.emailAddress,
    });
  } catch (error) {
    console.error("Send digest error:", error);
    return NextResponse.json(
      { error: "Failed to send digest email" },
      { status: 500 }
    );
  }
}

// GET endpoint to check email configuration status
export async function GET() {
  const configured = isEmailConfigured();
  
  return NextResponse.json({
    configured,
    message: configured 
      ? "Email is configured and ready" 
      : "RESEND_API_KEY not set. Add it to enable email sending.",
  });
}
