import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { sendSinglePostEmail, isEmailConfigured } from "@/lib/email";

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const userId = (session.user as any).id;
    const body = await request.json();
    const { postId, baseUrl } = body;

    if (!postId) {
      return NextResponse.json(
        { error: "postId is required" },
        { status: 400 }
      );
    }

    // Check if email is configured
    if (!isEmailConfigured()) {
      return NextResponse.json(
        {
          error: "Email not configured",
          message: "RESEND_API_KEY is not set. Add it to your environment to enable emails.",
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

    // Get the post
    const post = await prisma.post.findFirst({
      where: {
        id: postId,
        userId,
      },
    });

    if (!post) {
      return NextResponse.json(
        { error: "Post not found" },
        { status: 404 }
      );
    }

    // Get user name for email greeting
    const user = await prisma.user.findUnique({
      where: { id: userId },
      select: { firstName: true, email: true },
    });

    // Send the email
    const result = await sendSinglePostEmail({
      to: settings.emailAddress,
      userName: user?.firstName || user?.email?.split("@")[0] || "there",
      post: {
        id: post.id,
        topic: post.topic,
        content: post.content,
        tone: post.tone,
        contentType: post.contentType,
      },
      baseUrl: baseUrl || "",
    });

    if (!result.success) {
      return NextResponse.json(
        { error: result.error || "Failed to send email" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      messageId: result.messageId,
      sentTo: settings.emailAddress,
    });
  } catch (error) {
    console.error("Send single post email error:", error);
    return NextResponse.json(
      { error: "Failed to send email" },
      { status: 500 }
    );
  }
}
