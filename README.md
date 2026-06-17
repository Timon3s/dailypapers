# HF Daily Papers – AI Takeaways

An RSS feed of [Hugging Face Daily Papers](https://huggingface.co/papers) with **full-paper AI takeaways** powered by [Groq](https://groq.com) (free tier, no credit card required).

Unlike the default abstract-only summaries, this downloads the entire paper text and generates a richer 3–4 sentence takeaway covering the method, a concrete result with numbers, and an honest limitation.

## What it does

Every day at 07:00 UTC, a GitHub Actions workflow:

1. Fetches that day's Hugging Face Daily Papers (sorted by upvotes, up to 30).
2. Downloads the full text of each paper — via HF's Markdown rendering first, then the arXiv PDF as a fallback.
3. Sends the full text to Groq's free LLM API for a plain-language takeaway.
4. Publishes the result as a standard RSS 2.0 feed (`feed.xml` in this repo).

## 5-minute setup

1. **Create a public GitHub repo** and push these files to it.

2. **Get a free Groq API key** at [console.groq.com](https://console.groq.com) — no credit card needed, takes about a minute.

3. **Add the key as a repo secret:**
   Settings → Secrets and variables → Actions → New repository secret.
   Name: `GROQ_API_KEY`, Value: your key (starts with `gsk_...`).

4. **Run the workflow once manually:**
   Actions tab → "Daily Papers RSS" → Run workflow button.

5. **Subscribe to the feed** in your RSS reader:
   ```
   https://raw.githubusercontent.com/<your-username>/<your-repo>/main/feed.xml
   ```
   Works with any RSS reader: [Reeder](https://reeder.app), [NetNewsWire](https://netnewswire.com), [Feedly](https://feedly.com), [Inoreader](https://www.inoreader.com), and more.

### Optional: nicer URL via GitHub Pages

Enable GitHub Pages (Settings → Pages → Source: "Deploy from a branch" → branch: `main`, folder: `/`) and use `https://<username>.github.io/<repo>/feed.xml` instead of the raw link.

## Configuration

All environment variables are optional — the defaults work without any changes.

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(unset)* | Enables AI takeaways. Without it, HF's built-in one-line summaries are used instead. |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Which Groq model to use for summarization. |
| `MAX_FULLTEXT_CHARS` | `60000` | How many characters of full paper text to send to the LLM. |
| `MAX_PAPERS` | `30` | Maximum number of papers per day in the feed. |
| `FEED_PATH` | `feed.xml` | Output file name/path. |
| `FEED_PUBLIC_URL` | `https://huggingface.co/papers` | The feed's `<link>` element (shown in RSS readers). |

## Run locally

```bash
pip install -r requirements.txt
GROQ_API_KEY=gsk_... python generate_feed.py
```

On Windows (PowerShell):
```powershell
$env:GROQ_API_KEY = "gsk_..."
python generate_feed.py
```

The feed is written to `feed.xml` in the current directory.

## GitHub Actions minutes

**Public repos** get unlimited free GitHub Actions minutes.
**Private repos** get 2,000 free minutes/month — a once-a-day job uses roughly 30–60 minutes/month, well within the free tier.
