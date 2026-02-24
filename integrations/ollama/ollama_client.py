"""
Ollama Local LLM Client
Free inference on Mac mini Apple Silicon — saves Claude API budget for real conversations.

Usage:
    from integrations.ollama.ollama_client import ask, summarize, draft_email, score_lead

Default model: jarvis-local (llama3.2:3b with Jarvis system prompt)
Fast model:    llama3.2:3b
"""
import subprocess
import requests
import json
from pathlib import Path

OLLAMA_BASE  = "http://localhost:11434"
# Model routing — use the right tool for each job:
# qwen2.5:7b     — best local model, use for: lead scoring, email drafts, summarization, research
# jarvis-local   — qwen2.5:7b + Matt context, use for: personalized tasks, daily logs
# llama3.2:3b    — fastest, use for: simple classification, bulk processing
# nomic-embed    — embeddings only (for future second brain / RAG)

DEFAULT_MODEL = "qwen2.5:7b"     # Best quality for most local tasks
FAST_MODEL    = "llama3.2:3b"    # Speed over quality — bulk/simple tasks
EMBED_MODEL   = "nomic-embed-text"  # Embeddings for RAG/second brain

def is_running() -> bool:
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=2)
        return r.status_code == 200
    except:
        return False

def list_models() -> list:
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        return [m["name"] for m in r.json().get("models", [])]
    except:
        return []

def _generate(model: str, prompt: str, system: str = "", stream: bool = False) -> str:
    """Core generate call via Ollama REST API."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
    }
    if system:
        payload["system"] = system

    try:
        r = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json=payload,
            timeout=120,
            stream=stream,
        )
        r.raise_for_status()

        if stream:
            result = ""
            for line in r.iter_lines():
                if line:
                    data = json.loads(line)
                    result += data.get("response", "")
                    if data.get("done"):
                        break
            return result.strip()
        else:
            return r.json().get("response", "").strip()
    except Exception as e:
        return f"[Ollama error: {e}]"

def ask(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """General Q&A — use for lightweight questions to save API costs."""
    if not is_running():
        return "[Ollama not running — start with: brew services start ollama]"
    # Fallback if jarvis-local not yet created
    avail = list_models()
    if model not in avail:
        model = FAST_MODEL
    return _generate(model, prompt)

def summarize(text: str, context: str = "") -> str:
    """Summarize text. Context = purpose (e.g., 'for a morning briefing')."""
    suffix = f" {context}" if context else ""
    return ask(f"Summarize the following concisely{suffix}:\n\n{text}")

def draft_email(
    purpose: str,
    recipient: str = "",
    context: str = "",
    tone: str = "professional but warm"
) -> str:
    """Draft an email. Returns just the body text."""
    parts = [f"Draft a {tone} email with this purpose: {purpose}."]
    if recipient:
        parts.append(f"Recipient: {recipient}.")
    if context:
        parts.append(f"Context: {context}.")
    parts.append("Keep it concise. Output only the email body, no subject line.")
    return ask(" ".join(parts))

def score_lead(lead: dict) -> dict:
    """Score a real estate lead for life insurance prospecting.
    Returns {'score': int, 'reasoning': str, 'priority': 'hot'|'warm'|'cold'}
    """
    prompt = f"""You are scoring a real estate lead for a financial advisor selling life insurance.

Lead data:
{json.dumps(lead, indent=2)}

Score 1-10 (10=best) based on:
- Recent home purchase (within 6 months = very hot)
- Home value $700k+ suggests income/assets
- Young families (age 25-45) are best targets
- Recent life event (move, marriage, kids) = need for coverage

Return ONLY JSON: {{"score": <int>, "priority": "<hot|warm|cold>", "reasoning": "<1 sentence>"}}"""

    result = ask(prompt)
    try:
        # Extract JSON from response
        import re
        match = re.search(r'\{[^}]+\}', result, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return {"score": 5, "priority": "warm", "reasoning": result[:100]}

if __name__ == "__main__":
    print("Ollama status:", "running" if is_running() else "stopped")
    print("Models:", list_models())
    print("\nTest ask:")
    print(ask("What's 2+2? Answer in one word."))
