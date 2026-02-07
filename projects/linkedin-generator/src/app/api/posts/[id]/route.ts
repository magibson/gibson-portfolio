import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

// GET a single post
export async function GET(
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

    const post = await prisma.post.findFirst({
      where: { id, userId },
    });

    if (!post) {
      return NextResponse.json({ error: "Post not found" }, { status: 404 });
    }

    return NextResponse.json({
      id: post.id,
      topic: post.topic,
      tone: post.tone,
      contentType: post.contentType,
      content: post.content,
      status: post.status,
      editHistory: JSON.parse(post.editHistory),
      createdAt: post.createdAt.toISOString(),
      updatedAt: post.updatedAt.toISOString(),
    });
  } catch (error) {
    console.error("Failed to fetch post:", error);
    return NextResponse.json(
      { error: "Failed to fetch post" },
      { status: 500 }
    );
  }
}

// PUT to update a post
export async function PUT(
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
    const { content, status } = body;

    // Verify the post belongs to the user
    const existingPost = await prisma.post.findFirst({
      where: { id, userId },
    });

    if (!existingPost) {
      return NextResponse.json({ error: "Post not found" }, { status: 404 });
    }

    // Build update data
    const updateData: any = {};
    
    if (content !== undefined) {
      updateData.content = content;
      
      // Add to edit history if content changed
      if (content !== existingPost.content) {
        const history = JSON.parse(existingPost.editHistory);
        history.push({
          timestamp: new Date().toISOString(),
          previousContent: existingPost.content,
          newContent: content,
        });
        updateData.editHistory = JSON.stringify(history);
        updateData.status = "edited";
      }
    }
    
    if (status !== undefined) {
      updateData.status = status;
    }

    const post = await prisma.post.update({
      where: { id },
      data: updateData,
    });

    return NextResponse.json({
      id: post.id,
      topic: post.topic,
      tone: post.tone,
      contentType: post.contentType,
      content: post.content,
      status: post.status,
      editHistory: JSON.parse(post.editHistory),
      createdAt: post.createdAt.toISOString(),
      updatedAt: post.updatedAt.toISOString(),
    });
  } catch (error) {
    console.error("Failed to update post:", error);
    return NextResponse.json(
      { error: "Failed to update post" },
      { status: 500 }
    );
  }
}

// DELETE a post
export async function DELETE(
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

    // Verify the post belongs to the user
    const existingPost = await prisma.post.findFirst({
      where: { id, userId },
    });

    if (!existingPost) {
      return NextResponse.json({ error: "Post not found" }, { status: 404 });
    }

    await prisma.post.delete({
      where: { id },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Failed to delete post:", error);
    return NextResponse.json(
      { error: "Failed to delete post" },
      { status: 500 }
    );
  }
}
