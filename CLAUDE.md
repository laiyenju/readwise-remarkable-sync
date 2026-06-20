# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Automated daily sync from Readwise Reader → Google Drive → reMarkable 2. A GitHub Actions workflow runs `sync.py` every day at 00:30 Taiwan time (UTC `30 16 * * *`), fetches articles from Readwise, converts them to EPUB, and uploads them to a Google Drive folder that reMarkable's native Google Drive integration syncs to the device.

## Running the Script Locally

```bash
pip install -r requirements.txt

READWISE_TOKEN=... GDRIVE_FOLDER_ID=... GOOGLE_OAUTH_CREDENTIALS='...' python sync.py
```

There are no tests. To test without uploading, comment out `delete_old_files()` and `upload_epub()` in `main()`. The GitHub Actions workflow also has `workflow_dispatch` enabled — you can trigger it manually from the GitHub UI.

## Architecture

```
Readwise Reader API
  ↓  fetch_tagged_articles()   — tag=remarkable, all pages
  ↓  fetch_recent_articles()   — new/later locations, max 20 each
  ↓  merge_articles()          — dedup by article ID
  ↓  article_to_epub()         — HTML → EPUB via ebooklib
  ↓  upload_epub()             — upload to Google Drive folder
  ↓
reMarkable 2 (via native Google Drive integration)
```

## Required Secrets (GitHub Actions)

| Secret | Description |
|--------|-------------|
| `READWISE_TOKEN` | Readwise API token from readwise.io/access_token |
| `GDRIVE_FOLDER_ID` | Google Drive folder ID for the "Readwise Reader" folder |
| `GOOGLE_OAUTH_CREDENTIALS` | Full JSON with OAuth2 refresh token (not a Service Account) |

**Why OAuth2, not Service Account:** Service Accounts lack personal Drive quota and get 403 `storageQuotaExceeded`.

## Critical Implementation Constraints

### Readwise API
- Full article content is in `html_content`, not `html` — and only returned when `withHtmlContent=true` is passed.
- **Never** pass `withHtmlContent=true` to the list endpoint (pagination scan). With all articles' full HTML in one response, the JSON can hit 2–3MB per article and crash the process. Only `fetch_full_html()` uses this flag, on single-article requests by ID.
- Feed articles never have content — Readwise only stores metadata for them. Only `new`/`later` location articles have parsed HTML.
- Rate limit: 20 requests/minute. All requests use `API_DELAY = 3s` between calls, managed in `main()` (not inside individual functions).

### ebooklib / EPUB Format
- `chapter.content` must use plain `<html><body>...</body></html>` — no `<?xml ...?>` declaration, no `xmlns` XHTML namespace. ebooklib parses content with lxml in XML mode; Readwise's HTML is not valid XML and causes `Document is empty` if strict XML headers are added.
- `book.spine = [chapter, 'nav']` — chapter must come first. reMarkable opens the first spine item; putting `nav` first shows the table of contents instead of the article.

### Memory
- `MAX_HTML_CHARS = 300_000` (~300KB). Articles exceeding this (books, long reads) are truncated before EPUB creation.

## Article Selection Logic

| Source | Filter | Cap |
|--------|--------|-----|
| Tagged articles | `tag=remarkable` | None (all pages fetched) |
| Recent saved | `location=new` + `location=later` | 20 articles total |

Both sources are merged and deduped by article ID before conversion.
