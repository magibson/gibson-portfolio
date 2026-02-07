import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    
    const userId = (session.user as any).id;
    
    const examples = await prisma.writingExample.findMany({
      where: { userId },
      orderBy: { createdAt: "desc" },
    });
    
    return NextResponse.json({ examples });
  } catch (error) {
    console.error("Writing examples GET error:", error);
    return NextResponse.json({ error: "Failed to get examples" }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    
    const userId = (session.user as any).id;
    const { content, source } = await request.json();
    
    if (!content?.trim()) {
      return NextResponse.json({ error: "Content is required" }, { status: 400 });
    }
    
    const example = await prisma.writingExample.create({
      data: {
        userId,
        content: content.trim(),
        source: source || "manual",
      },
    });
    
    return NextResponse.json({ success: true, example });
  } catch (error) {
    console.error("Writing examples POST error:", error);
    return NextResponse.json({ error: "Failed to add example" }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    
    const userId = (session.user as any).id;
    const { searchParams } = new URL(request.url);
    const id = searchParams.get("id");
    
    if (!id) {
      return NextResponse.json({ error: "ID is required" }, { status: 400 });
    }
    
    // Verify ownership before deleting
    const example = await prisma.writingExample.findUnique({
      where: { id },
    });
    
    if (!example || example.userId !== userId) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    
    await prisma.writingExample.delete({
      where: { id },
    });
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Writing examples DELETE error:", error);
    return NextResponse.json({ error: "Failed to delete example" }, { status: 500 });
  }
}
