/**
 * Gemini API helper with retry logic for rate limiting (429)
 */

interface GeminiMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

interface GeminiOptions {
  model?: string;
  temperature?: number;
  max_tokens?: number;
  maxRetries?: number;
  baseDelayMs?: number;
}

export async function callGemini(
  messages: GeminiMessage[],
  options: GeminiOptions = {}
): Promise<string> {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) throw new Error("Gemini API key not configured");

  const {
    model = "gemini-2.0-flash",
    temperature = 0.7,
    max_tokens = 1000,
    maxRetries = 3,
    baseDelayMs = 2000,
  } = options;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await fetch(
      "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model,
          messages,
          temperature,
          max_tokens,
        }),
      }
    );

    if (response.ok) {
      const data = await response.json();
      const content = data.choices?.[0]?.message?.content;
      if (!content) throw new Error("No content generated");
      return content;
    }

    if (response.status === 429 && attempt < maxRetries) {
      const delay = baseDelayMs * Math.pow(2, attempt); // 2s, 4s, 8s
      console.log(`Gemini 429 rate limit - retrying in ${delay}ms (attempt ${attempt + 1}/${maxRetries})`);
      await new Promise((r) => setTimeout(r, delay));
      continue;
    }

    const errorText = await response.text();
    console.error("Gemini API error:", errorText);
    throw new Error(`Gemini API error (${response.status}): ${errorText}`);
  }

  throw new Error("Gemini API: max retries exceeded");
}
