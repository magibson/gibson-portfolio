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
    
    // Get user info (firstName, email)
    const user = await prisma.user.findUnique({
      where: { id: userId },
      select: { firstName: true, email: true },
    });
    
    const settings = await prisma.userSettings.findUnique({
      where: { userId },
    });
    
    if (!settings) {
      // Create default settings if they don't exist
      const newSettings = await prisma.userSettings.create({
        data: {
          userId,
          postsPerBatch: 5,
          batchCount: 1,
          postLength: "medium",
          sourceWebsites: "[]",
          audience: "young-professionals",
          customTopics: "[]",
          schedules: "[]",
          emailAddress: user?.email || null,
        },
      });
      
      return NextResponse.json({
        postsPerBatch: newSettings.postsPerBatch,
        batchCount: newSettings.batchCount,
        postLength: newSettings.postLength,
        emailAddress: newSettings.emailAddress || user?.email || "",
        sourceWebsites: JSON.parse(newSettings.sourceWebsites),
        audience: newSettings.audience,
        customTopics: JSON.parse(newSettings.customTopics),
        schedules: JSON.parse(newSettings.schedules),
        writingStyle: "",
        firstName: user?.firstName || "",
        userEmail: user?.email || "",
      });
    }
    
    // Get writing examples to include as writingStyle
    const writingExamples = await prisma.writingExample.findMany({
      where: { userId },
      orderBy: { createdAt: "desc" },
    });
    
    const writingStyle = writingExamples.map(e => e.content).join("\n\n---\n\n");
    
    return NextResponse.json({
      postsPerBatch: settings.postsPerBatch,
      batchCount: settings.batchCount,
      postLength: settings.postLength,
      emailAddress: settings.emailAddress || user?.email || "",
      sourceWebsites: JSON.parse(settings.sourceWebsites),
      audience: settings.audience || "young-professionals",
      customTopics: JSON.parse(settings.customTopics || "[]"),
      schedules: JSON.parse(settings.schedules),
      aiInstructions: settings.aiInstructions || "",
      writingStyle,
      firstName: user?.firstName || "",
      userEmail: user?.email || "",
    });
  } catch (error) {
    console.error("Settings GET error:", error);
    return NextResponse.json({ error: "Failed to get settings" }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    
    const userId = (session.user as any).id;
    const body = await request.json();
    
    const {
      postsPerBatch,
      batchCount,
      postLength,
      emailAddress,
      sourceWebsites,
      audience,
      customTopics,
      schedules,
      aiInstructions,
    } = body;
    
    const settings = await prisma.userSettings.upsert({
      where: { userId },
      update: {
        postsPerBatch: postsPerBatch ?? 5,
        batchCount: batchCount ?? 1,
        postLength: postLength ?? "medium",
        emailAddress: emailAddress || null,
        sourceWebsites: JSON.stringify(sourceWebsites ?? []),
        audience: audience ?? "young-professionals",
        customTopics: JSON.stringify(customTopics ?? []),
        schedules: JSON.stringify(schedules ?? []),
        aiInstructions: aiInstructions ?? "",
      },
      create: {
        userId,
        postsPerBatch: postsPerBatch ?? 5,
        batchCount: batchCount ?? 1,
        postLength: postLength ?? "medium",
        emailAddress: emailAddress || null,
        sourceWebsites: JSON.stringify(sourceWebsites ?? []),
        audience: audience ?? "young-professionals",
        customTopics: JSON.stringify(customTopics ?? []),
        schedules: JSON.stringify(schedules ?? []),
        aiInstructions: aiInstructions ?? "",
      },
    });
    
    return NextResponse.json({
      success: true,
      settings: {
        postsPerBatch: settings.postsPerBatch,
        batchCount: settings.batchCount,
        postLength: settings.postLength,
        emailAddress: settings.emailAddress || "",
        sourceWebsites: JSON.parse(settings.sourceWebsites),
        audience: settings.audience,
        customTopics: JSON.parse(settings.customTopics || "[]"),
        schedules: JSON.parse(settings.schedules),
      },
    });
  } catch (error) {
    console.error("Settings PUT error:", error);
    return NextResponse.json({ error: "Failed to save settings" }, { status: 500 });
  }
}
