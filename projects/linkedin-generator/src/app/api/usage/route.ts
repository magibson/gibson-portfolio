import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

const WEEKLY_LIMIT = 20; // Posts per user per week

export async function GET(req: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    if (!session?.user?.email) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const user = await prisma.user.findUnique({
      where: { email: session.user.email },
    });

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    // Calculate start of current week (Sunday)
    const now = new Date();
    const dayOfWeek = now.getDay();
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - dayOfWeek);
    startOfWeek.setHours(0, 0, 0, 0);

    // Calculate end of week (next Sunday)
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 7);

    // Count posts created this week
    const postsThisWeek = await prisma.post.count({
      where: {
        userId: user.id,
        createdAt: {
          gte: startOfWeek,
        },
      },
    });

    const remaining = Math.max(0, WEEKLY_LIMIT - postsThisWeek);
    
    // Format reset time
    const daysUntilReset = 7 - dayOfWeek;
    let resetsAt: string;
    if (daysUntilReset === 0) {
      resetsAt = "tomorrow";
    } else if (daysUntilReset === 1) {
      resetsAt = "tomorrow";
    } else {
      resetsAt = `in ${daysUntilReset} days`;
    }

    return NextResponse.json({
      used: postsThisWeek,
      limit: WEEKLY_LIMIT,
      remaining,
      resetsAt,
      weekStart: startOfWeek.toISOString(),
    });
  } catch (error) {
    console.error("Usage fetch error:", error);
    return NextResponse.json(
      { error: "Failed to fetch usage" },
      { status: 500 }
    );
  }
}
