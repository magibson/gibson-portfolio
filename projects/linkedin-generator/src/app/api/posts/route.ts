import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

// GET all posts for the current user
export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const userId = (session.user as any).id;

    // Get user settings for audience info
    const settings = await prisma.userSettings.findUnique({
      where: { userId },
      select: { audience: true },
    });

    const posts = await prisma.post.findMany({
      where: { userId },
      orderBy: { createdAt: "desc" },
      include: {
        batch: {
          select: {
            id: true,
            scheduledFor: true,
            generatedAt: true,
          },
        },
      },
    });

    return NextResponse.json({
      posts: posts.map((post) => ({
        id: post.id,
        topic: post.topic,
        tone: post.tone,
        contentType: post.contentType,
        content: post.content,
        status: post.status,
        sourceArticleUrl: post.sourceArticleUrl,
        sourceArticleTitle: post.sourceArticleTitle,
        sourceArticleImage: post.sourceArticleImage,
        audience: post.audience,
        createdAt: post.createdAt.toISOString(),
        updatedAt: post.updatedAt.toISOString(),
        batch: post.batch
          ? {
              id: post.batch.id,
              scheduledFor: post.batch.scheduledFor.toISOString(),
              generatedAt: post.batch.generatedAt?.toISOString() || null,
            }
          : null,
      })),
      audience: settings?.audience || "young-professionals",
    });
  } catch (error) {
    console.error("Failed to fetch posts:", error);
    return NextResponse.json(
      { error: "Failed to fetch posts" },
      { status: 500 }
    );
  }
}
