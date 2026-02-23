"""
ingest.py — Ingestion engine for the Second Brain
Handles: text, URLs, PDFs, audio (Whisper), images
"""
import os
import sys
import json
import tempfile
from pathlib import Path
from urllib.parse import urlparse

# Load env
env_path = Path.home() / "clawd" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from storage import save_document

REQUEST_TIMEOUT = 30

# ── URL ────────────────────────────────────────────────────────────────────────

def _scrape_url(url: str) -> tuple[str, str]:
    """Returns (title, body_text)."""
    import requests
    from bs4 import BeautifulSoup

    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    r = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # Remove junk
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title else urlparse(url).netloc

    # Try article/main first, else full body
    content_tag = soup.find("article") or soup.find("main") or soup.find("body")
    body_text = content_tag.get_text(separator="\n", strip=True) if content_tag else ""
    # Collapse excessive whitespace
    import re
    body_text = re.sub(r'\n{3,}', '\n\n', body_text).strip()

    return title, body_text[:15000]  # cap at 15k chars


def ingest_url(url: str, tags: list = None) -> str:
    tags = tags or []
    print(f"[brain] Scraping {url}...")
    try:
        title, body_text = _scrape_url(url)
        doc_id = save_document(
            content_type="url",
            body_text=body_text,
            title=title,
            source=url,
            tags=tags,
            metadata={"url": url}
        )
        print(f"[brain] Saved URL: '{title}' → {doc_id[:8]}")
        return doc_id
    except Exception as e:
        print(f"[brain] URL ingest failed: {e}")
        raise


# ── TEXT ───────────────────────────────────────────────────────────────────────

def ingest_text(text: str, title: str = "", tags: list = None, source: str = "manual") -> str:
    tags = tags or []
    title = title or text[:60].replace("\n", " ")
    doc_id = save_document(
        content_type="text",
        body_text=text,
        title=title,
        source=source,
        tags=tags,
    )
    print(f"[brain] Saved text: '{title[:50]}' → {doc_id[:8]}")
    return doc_id


# ── PDF ────────────────────────────────────────────────────────────────────────

def ingest_pdf(file_path: str, tags: list = None) -> str:
    import pdfplumber
    tags = tags or []
    path = Path(file_path)
    print(f"[brain] Reading PDF: {path.name}...")
    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        body_text = "\n\n".join(p.strip() for p in pages if p.strip())
        doc_id = save_document(
            content_type="pdf",
            body_text=body_text[:20000],
            title=path.stem,
            source=str(path.resolve()),
            tags=tags,
            metadata={"pages": len(pages), "filename": path.name}
        )
        print(f"[brain] Saved PDF: '{path.name}' ({len(pages)} pages) → {doc_id[:8]}")
        return doc_id
    except Exception as e:
        print(f"[brain] PDF ingest failed: {e}")
        raise


# ── AUDIO (Whisper via OpenAI API) ─────────────────────────────────────────────

def ingest_audio(file_path: str, tags: list = None) -> str:
    from openai import OpenAI
    tags = tags or []
    path = Path(file_path)
    print(f"[brain] Transcribing audio: {path.name}...")
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        with open(str(path), "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text"
            )
        transcript = result if isinstance(result, str) else result.text
        doc_id = save_document(
            content_type="audio",
            body_text=transcript,
            title=f"Voice note: {path.stem}",
            source=str(path.resolve()),
            tags=tags,
            metadata={"filename": path.name, "transcript": True}
        )
        print(f"[brain] Saved audio transcript: '{path.name}' → {doc_id[:8]}")
        return doc_id
    except Exception as e:
        print(f"[brain] Audio ingest failed: {e}")
        raise


# ── IMAGE ──────────────────────────────────────────────────────────────────────

def ingest_image(file_path: str, caption: str = "", tags: list = None) -> str:
    tags = tags or []
    path = Path(file_path)
    body_text = caption or f"Image file: {path.name}"
    doc_id = save_document(
        content_type="image",
        body_text=body_text,
        title=caption or path.stem,
        source=str(path.resolve()),
        tags=tags,
        metadata={"filename": path.name}
    )
    print(f"[brain] Saved image: '{path.name}' → {doc_id[:8]}")
    return doc_id


# ── AUTO-DETECT ────────────────────────────────────────────────────────────────

def ingest(content: str, tags: list = None) -> str:
    """Auto-detect content type and ingest."""
    tags = tags or []
    content = content.strip()

    if content.startswith("http://") or content.startswith("https://"):
        return ingest_url(content, tags=tags)

    p = Path(content)
    if p.exists():
        ext = p.suffix.lower()
        if ext == ".pdf":
            return ingest_pdf(content, tags=tags)
        if ext in {".mp3", ".m4a", ".wav", ".ogg", ".webm", ".mp4"}:
            return ingest_audio(content, tags=tags)
        if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"}:
            return ingest_image(content, tags=tags)
        # Plain text file
        return ingest_text(p.read_text(), title=p.stem, tags=tags, source=str(p))

    return ingest_text(content, tags=tags)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <url|text|file_path> [tag1,tag2,...]")
        sys.exit(1)
    content = sys.argv[1]
    tags = sys.argv[2].split(",") if len(sys.argv) > 2 else []
    ingest(content, tags=tags)
