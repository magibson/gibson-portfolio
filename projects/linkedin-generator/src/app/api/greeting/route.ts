import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

const DAYS_OF_WEEK = [
  "Sunday",
  "Monday", 
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];

export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    
    const userId = (session?.user as any)?.id;
    if (!userId) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    // Get user's first name
    const user = await prisma.user.findUnique({
      where: { id: userId },
      select: { firstName: true, email: true },
    });

    const rawName = user?.firstName || user?.email?.split("@")[0] || "friend";
    const firstName = rawName.charAt(0).toUpperCase() + rawName.slice(1).toLowerCase();
    // Use Eastern time for day/time calculations
    const now = new Date();
    const eastern = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }));
    const dayOfWeek = DAYS_OF_WEEK[eastern.getDay()];
    const hour = eastern.getHours();
    
    // Determine time of day
    let timeOfDay = "day";
    if (hour < 12) timeOfDay = "morning";
    else if (hour < 17) timeOfDay = "afternoon";
    else timeOfDay = "evening";

    // Check if Gemini API key is available
    const apiKey = process.env.GEMINI_API_KEY;
    
    if (!apiKey) {
      // Fallback greeting
      const fallbacks = [
        `${firstName}! Ready to generate some "authentic" content?`,
        `${firstName}, your prospects are waiting. Let's give them something good.`,
        `Ah ${firstName}, back to dominate the LinkedIn algorithm.`,
      ];
      return NextResponse.json({
        greeting: fallbacks[Math.floor(Math.random() * fallbacks.length)],
        fallback: true,
      });
    }

    // Call Gemini API
    const prompt = `Generate a single short, funny greeting for a financial advisor named "${firstName}" who's using a LinkedIn content generator. It's ${dayOfWeek} ${timeOfDay}.

Context: This is a tool that helps financial advisors create LinkedIn posts. Be self-aware about:
- The grind of being a financial advisor
- LinkedIn "thought leadership" culture
- Prospecting and finding clients
- The hustle of building a book of business
- The irony of AI writing "authentic" content

Requirements:
- Actually funny - make them laugh or smirk
- Self-aware and meta about what this tool does
- Can poke fun at the job, clients, social media, prospecting
- Safe for work but edgy/sarcastic humor is great
- Maximum 1-2 sentences
- No quotes around your response
- Just output the greeting, nothing else

Example vibes:
- ${firstName}! Ready to generate some "authentic thought leadership"? The algorithm awaits.
- Ah ${firstName}, back to convince LinkedIn you're a financial guru. Let's make magic.
- ${firstName}! Time to pretend you wrote these posts yourself. Your secret's safe.
- Look who needs more content to impress prospects. ${firstName}'s in the building.
- ${firstName}, your future clients are scrolling LinkedIn right now. Let's give them something good.
- Another ${dayOfWeek}, another chance to out-post your competition. Let's go ${firstName}.`;

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          contents: [
            {
              parts: [{ text: prompt }],
            },
          ],
          generationConfig: {
            temperature: 0.9,
            maxOutputTokens: 100,
          },
          safetySettings: [
            {
              category: "HARM_CATEGORY_HARASSMENT",
              threshold: "BLOCK_MEDIUM_AND_ABOVE",
            },
            {
              category: "HARM_CATEGORY_HATE_SPEECH",
              threshold: "BLOCK_MEDIUM_AND_ABOVE",
            },
            {
              category: "HARM_CATEGORY_SEXUALLY_EXPLICIT",
              threshold: "BLOCK_MEDIUM_AND_ABOVE",
            },
            {
              category: "HARM_CATEGORY_DANGEROUS_CONTENT",
              threshold: "BLOCK_MEDIUM_AND_ABOVE",
            },
          ],
        }),
      }
    );

    if (!response.ok) {
      console.error("Gemini API error:", await response.text());
      return NextResponse.json({
        greeting: `Welcome back, ${firstName}!`,
        fallback: true,
      });
    }

    const data = await response.json();
    const greeting = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim();

    if (!greeting) {
      return NextResponse.json({
        greeting: `Welcome back, ${firstName}!`,
        fallback: true,
      });
    }

    // Ensure name is in the greeting (sometimes Gemini forgets)
    const finalGreeting = greeting.includes(firstName) 
      ? greeting 
      : `Hey ${firstName}! ${greeting}`;

    return NextResponse.json({
      greeting: finalGreeting,
      fallback: false,
    }, {
      headers: {
        'Cache-Control': 'no-store, no-cache, must-revalidate',
      },
    });
  } catch (error) {
    console.error("Greeting API error:", error);
    return NextResponse.json({
      greeting: "Welcome back, friend!",
      fallback: true,
    }, {
      headers: {
        'Cache-Control': 'no-store, no-cache, must-revalidate',
      },
    });
  }
}
