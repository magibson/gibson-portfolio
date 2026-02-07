import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { curateArticles, suggestTopicsFromArticles } from "@/lib/curation";
import { AudienceType } from "@/lib/types";

export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const userId = (session.user as any).id;

    // Get user settings
    const settings = await prisma.userSettings.findUnique({
      where: { userId },
    });

    if (!settings) {
      return NextResponse.json(
        { error: "Please configure your settings first" },
        { status: 400 }
      );
    }

    const sourceWebsites = JSON.parse(settings.sourceWebsites || "[]") as string[];
    const customTopics = JSON.parse(settings.customTopics || "[]") as string[];
    const audience = (settings.audience || "young-professionals") as AudienceType;

    if (sourceWebsites.length === 0) {
      return NextResponse.json({
        articles: [],
        errors: [],
        suggestedTopics: [],
        message: "No source websites configured. Add sources in Settings.",
      });
    }

    // Parse optional query params
    const searchParams = request.nextUrl.searchParams;
    const maxDays = parseInt(searchParams.get("maxDays") || "7", 10);
    const maxArticles = parseInt(searchParams.get("maxArticles") || "30", 10);

    // Curate articles
    const result = await curateArticles(sourceWebsites, audience, customTopics, {
      maxDays,
      maxTotalArticles: maxArticles,
    });

    // Suggest topics based on what was found
    const suggestedTopics = suggestTopicsFromArticles(result.articles);

    return NextResponse.json({
      articles: result.articles,
      errors: result.errors,
      suggestedTopics,
      fetchedAt: result.fetchedAt,
      settings: {
        audience,
        sourceCount: sourceWebsites.length,
      },
    });
  } catch (error) {
    console.error("Curation error:", error);
    return NextResponse.json(
      { error: "Failed to curate articles" },
      { status: 500 }
    );
  }
}

// POST endpoint for ad-hoc curation with custom sources
export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();
    const {
      sourceWebsites,
      audience = "young-professionals",
      customTopics = [],
      maxDays = 7,
      maxArticles = 30,
    } = body;

    if (!sourceWebsites || !Array.isArray(sourceWebsites) || sourceWebsites.length === 0) {
      return NextResponse.json(
        { error: "sourceWebsites array is required" },
        { status: 400 }
      );
    }

    const result = await curateArticles(
      sourceWebsites,
      audience as AudienceType,
      customTopics,
      {
        maxDays,
        maxTotalArticles: maxArticles,
      }
    );

    const suggestedTopics = suggestTopicsFromArticles(result.articles);

    return NextResponse.json({
      articles: result.articles,
      errors: result.errors,
      suggestedTopics,
      fetchedAt: result.fetchedAt,
    });
  } catch (error) {
    console.error("Curation error:", error);
    return NextResponse.json(
      { error: "Failed to curate articles" },
      { status: 500 }
    );
  }
}
