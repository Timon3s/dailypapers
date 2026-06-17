import os
import sys
import time
import datetime
import io

import requests
import pypdf
from feedgen.feed import FeedGenerator

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_FULLTEXT_CHARS = int(os.environ.get("MAX_FULLTEXT_CHARS", "60000"))
MAX_PAPERS = int(os.environ.get("MAX_PAPERS", "30"))
FEED_PATH = os.environ.get("FEED_PATH", "feed.xml")
FEED_PUBLIC_URL = os.environ.get("FEED_PUBLIC_URL", "https://huggingface.co/papers")

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


def fetch_latest_papers():
    for days_back in range(5):
        date = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
        try:
            resp = requests.get(
                "https://huggingface.co/api/daily_papers",
                params={"date": date, "limit": 100},
                timeout=30,
            )
            resp.raise_for_status()
            papers = resp.json()
            if papers:
                print(f"Fetched {len(papers)} papers for {date}", file=sys.stderr)
                return papers
        except Exception as e:
            print(f"Error fetching papers for {date}: {e}", file=sys.stderr)
    return []


def fetch_full_text(arxiv_id):
    # Method 1: HF Markdown (full paper as clean text)
    try:
        resp = requests.get(
            f"https://huggingface.co/papers/{arxiv_id}.md",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        if resp.status_code == 200 and len(resp.text) >= 3000:
            return resp.text
    except Exception as e:
        print(f"HF .md fetch failed for {arxiv_id}: {e}", file=sys.stderr)

    # Method 2: arXiv PDF fallback
    try:
        resp = requests.get(
            f"https://arxiv.org/pdf/{arxiv_id}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=60,
        )
        if resp.status_code == 200:
            reader = pypdf.PdfReader(io.BytesIO(resp.content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if text.strip():
                return text
    except Exception as e:
        print(f"arXiv PDF fetch failed for {arxiv_id}: {e}", file=sys.stderr)

    return ""


def call_groq(prompt):
    if not GROQ_API_KEY:
        return ""
    try:
        resp = requests.post(
            GROQ_ENDPOINT,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Groq API error: {e}", file=sys.stderr)
        return ""


def summarize(title, arxiv_id, abstract):
    """Returns (takeaway, source) where source is 'full_paper', 'abstract', or 'hf_summary'."""
    if not GROQ_API_KEY:
        return "", "hf_summary"

    full_text = fetch_full_text(arxiv_id)
    if full_text.strip():
        prompt = (
            f"Paper title: {title}\n\n"
            f"Full paper text:\n{full_text[:MAX_FULLTEXT_CHARS]}\n\n"
            "Write a full paragraph plain-language takeaway covering: "
            "(a) what's actually new / the method / used techniques / how it works, "
            "(b) the key result or finding with a concrete number if the paper gives one + potential / targeted applications, and "
            "(c) one honest caveat or limitation if the paper states one. "
            "No preamble."
        )
        takeaway = call_groq(prompt)
        if takeaway:
            return takeaway, "full_paper"

    # Fall back to abstract-only prompt
    prompt = (
        f"Paper title: {title}\n\n"
        f"Abstract only (full text unavailable):\n{abstract}\n\n"
        "Write a 4-5 sentence plain-language takeaway and explain why it matters. "
        "No preamble."
    )
    takeaway = call_groq(prompt)
    return takeaway, "abstract"


def item_description(paper_item, takeaway, source):
    p = paper_item.get("paper", {})
    upvotes = p.get("upvotes", 0)
    authors = p.get("authors", [])
    names = [a.get("name", "") for a in authors[:5]]
    author_str = ", ".join(names)
    if len(authors) > 5:
        author_str += " et al."
    github_repo = p.get("githubRepo", "")
    github_stars = p.get("githubStars", "")
    abstract = p.get("summary") or paper_item.get("summary", "")

    label = {
        "full_paper": "Takeaway (from full paper)",
        "abstract": "Takeaway (from abstract only)",
        "hf_summary": "Takeaway (from HF/abstract summary)",
    }.get(source, "Takeaway")

    parts = []
    if takeaway:
        parts.append(f"<p><strong>{label}:</strong> {takeaway}</p>")

    meta = [f"Upvotes: {upvotes}"]
    if author_str:
        meta.append(f"Authors: {author_str}")
    if github_repo:
        stars = f" ({github_stars}★)" if github_stars else ""
        meta.append(f'<a href="{github_repo}">GitHub{stars}</a>')
    parts.append(f"<p>{' | '.join(meta)}</p>")

    if abstract:
        parts.append(f"<p><strong>Abstract:</strong> {abstract}</p>")

    return "\n".join(parts)


def build_feed(entries):
    fg = FeedGenerator()
    fg.title("HF Daily Papers – AI Takeaways")
    fg.link(href=FEED_PUBLIC_URL)
    fg.description("Hugging Face Daily Papers with full-paper AI takeaways via Groq.")
    fg.language("en")
    fg.lastBuildDate(datetime.datetime.now(datetime.timezone.utc))

    for entry in entries:
        paper_item = entry["paper_item"]
        p = paper_item.get("paper", {})
        arxiv_id = p.get("id", "")
        title = p.get("title") or paper_item.get("title", "Untitled")
        published_at = paper_item.get("publishedAt", "")

        try:
            pub_dt = datetime.datetime.fromisoformat(published_at.rstrip("Z")).replace(
                tzinfo=datetime.timezone.utc
            )
        except Exception:
            pub_dt = datetime.datetime.now(datetime.timezone.utc)

        fe = fg.add_entry()
        fe.id(f"https://huggingface.co/papers/{arxiv_id}")
        fe.link(href=f"https://huggingface.co/papers/{arxiv_id}")
        fe.title(title)
        fe.pubDate(pub_dt)
        fe.description(item_description(paper_item, entry["takeaway"], entry["source"]))

    fg.rss_file(FEED_PATH)
    print(f"Feed written to {FEED_PATH}", file=sys.stderr)


def main():
    papers = fetch_latest_papers()
    if not papers:
        print("No papers found.", file=sys.stderr)
        sys.exit(0)

    papers.sort(key=lambda x: x.get("paper", {}).get("upvotes", 0), reverse=True)
    papers = papers[:MAX_PAPERS]

    entries = []
    for i, paper_item in enumerate(papers):
        p = paper_item.get("paper", {})
        arxiv_id = p.get("id", "")
        title = p.get("title") or paper_item.get("title", "Untitled")
        abstract = p.get("summary") or paper_item.get("summary", "")

        print(f"[{i + 1}/{len(papers)}] {title[:70]}", file=sys.stderr)

        takeaway, source = summarize(title, arxiv_id, abstract)

        if not takeaway:
            takeaway = p.get("ai_summary", "")
            source = "hf_summary"

        entries.append({"paper_item": paper_item, "takeaway": takeaway, "source": source})

        if GROQ_API_KEY:
            time.sleep(0.5)

    build_feed(entries)


if __name__ == "__main__":
    main()
