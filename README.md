English | [繁體中文](README.zh-TW.md)

# Readwise Reader → reMarkable 2 Automatic Sync

Automatically push articles from Readwise Reader to your reMarkable 2 every day, so you can read your saved articles on e-paper.

---

## What is this

This project uses **GitHub Actions** (a free cloud automation service) to run every day at 00:30 Taiwan time:

1. Fetch articles tagged `remarkable` in Readwise Reader, along with recently saved articles
2. Convert them to EPUB format (supported by reMarkable 2)
3. Upload them to a specified Google Drive folder
4. reMarkable 2 automatically syncs via its native Google Drive integration

**No need to keep your computer on.** Once set up, the entire workflow runs automatically in the cloud.

```
Readwise Reader
      ↓  GitHub Actions (triggers automatically at 00:30 daily)
   Google Drive "Readwise Reader" folder
      ↓  reMarkable native Google Drive integration
   reMarkable 2 device
```

---

## Prerequisites

| Item | Notes |
|------|-------|
| [Readwise Reader](https://readwise.io/read) account | Paid plan required |
| Google account | A regular Gmail account works |
| reMarkable 2 | Requires a [Connect](https://remarkable.com/store/connect) subscription for Google Drive integration |
| [GitHub](https://github.com) account | Free plan is sufficient |
| A computer (Mac or Windows) | Required to run a script once during setup |

---

## Setup

### Step 1: Fork this repo

1. Click the **Fork** button in the top-right corner of this page
2. Select your GitHub account to create a copy
3. All further configuration happens in your own repo

---

### Step 2: Get your Readwise API Token

1. Go to [readwise.io/access_token](https://readwise.io/access_token)
2. Copy the token shown on the page (a string of alphanumeric characters)
3. Save it somewhere — you'll need it in Step 6

---

### Step 3: Set up Google Cloud (get OAuth credentials)

This is the most involved part of the setup. Follow each sub-step carefully.

> **Why is this needed?** GitHub Actions needs your authorization to upload files to your Google Drive.

#### 3.1 Create a Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and sign in with your Google account
2. Click the project dropdown at the top of the page
3. Click **New Project**
4. Name it `readwise-remarkable` and click **Create**

#### 3.2 Enable the Google Drive API

1. Make sure the active project is `readwise-remarkable`
2. Go to [Enable Google Drive API](https://console.developers.google.com/apis/api/drive.googleapis.com)
3. Click **Enable**

#### 3.3 Configure the OAuth consent screen

1. In the left sidebar, click **APIs & Services** → **OAuth consent screen**
2. Set User Type to **External**, then click **Create**
3. Fill in the required fields:
   - **App name**: `Readwise Sync` (anything works)
   - **User support email**: your Gmail
   - **Developer contact information**: your Gmail
4. Click **Save and Continue**
5. On the **Scopes** page: click **Add or Remove Scopes**, search for and check `https://www.googleapis.com/auth/drive`, then click **Update** → **Save and Continue**
6. On the **Test users** page: click **Add Users**, enter your Gmail, then click **Save and Continue**
7. Click **Back to Dashboard**

#### 3.3.1 Publish the app (important)

> ⚠️ **Do not skip this step.** While the app is in test mode, the refresh token expires after **7 days**, after which GitHub Actions will fail with `invalid_grant: Token has been expired or revoked.`

1. In the left sidebar, click **OAuth consent screen** → **Audience**
2. Find the **Publishing status** section
3. Click **Publish App** → Confirm

Once published, the refresh token remains valid indefinitely — no periodic renewal needed.

#### 3.4 Create OAuth client credentials

1. In the left sidebar, click **Credentials**
2. Click **+ Create Credentials** → **OAuth client ID**
3. Set Application type to **Desktop app**
4. Name it `readwise-sync` (anything works), then click **Create**
5. In the dialog that appears, click **Download JSON** and save the file to your computer (e.g. Desktop)

#### 3.5 Run the authorization script locally

This step needs to be run once on your computer to obtain a refresh token.

**Mac:**

Open Terminal and run the following commands one at a time:

```bash
pip install google-auth-oauthlib
```

```bash
python get_token.py ~/Desktop/client_secret_xxx.json
```

> Replace `client_secret_xxx.json` with the actual filename of the file you downloaded.

**Windows:**

Open Command Prompt and run:

```
pip install google-auth-oauthlib
python get_token.py C:\Users\YourName\Desktop\client_secret_xxx.json
```

Your browser will open a Google authorization page — sign in and click **Allow**.

Back in the terminal, you'll see output like the following. **Copy the entire JSON block** (from `{` to the closing `}`):

```json
{
  "token": "...",
  "refresh_token": "...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "...",
  "client_secret": "...",
  "scopes": ["https://www.googleapis.com/auth/drive"]
}
```

Save it somewhere — you'll need it in Step 6.

---

### Step 4: Create a Google Drive folder

1. Go to [Google Drive](https://drive.google.com/)
2. Create a new folder named `Readwise Reader`
3. Open the folder and look at the URL in your browser:
   ```
   https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ
   ```
4. Copy the alphanumeric string at the end (`1aBcDeFgHiJkLmNoPqRsTuVwXyZ`) — that's the folder ID

---

### Step 5: Connect reMarkable 2 to Google Drive

1. On your reMarkable 2, go to **Settings → Storage → Google Drive**
2. Tap **Connect** and complete Google account authorization
3. Select the **Readwise Reader** folder you just created for sync
4. Return to the rM2 home screen — you should see the "Readwise Reader" folder appear

---

### Step 6: Add GitHub Secrets

GitHub Secrets store sensitive values securely. The script reads them at runtime without ever exposing them in code.

1. Go to your forked repo on GitHub
2. Click the **Settings** tab
3. In the left sidebar, go to **Secrets and variables** → **Actions**
4. Click **New repository secret** and add the following three secrets:

| Name | Value |
|------|-------|
| `READWISE_TOKEN` | The Readwise API token from Step 2 |
| `GDRIVE_FOLDER_ID` | The Google Drive folder ID from Step 4 |
| `GOOGLE_OAUTH_CREDENTIALS` | The full JSON from Step 3 (including `{` and `}`) |

---

### Step 7: Test the workflow

1. In your repo, click the **Actions** tab
2. In the left sidebar, click **Readwise → reMarkable Daily Sync**
3. Click **Run workflow** → **Run workflow** (green button)
4. Wait 2–5 minutes — a green checkmark ✅ means success
5. Go to your Google Drive "Readwise Reader" folder and confirm the EPUB files are there
6. Check your rM2 to confirm the articles synced (rM2 must be connected to Wi-Fi)

---

## Customization

A few constants at the top of `sync.py` can be adjusted:

```python
REMARKABLE_TAG = 'remarkable'   # the tag used to mark articles for sync
MAX_INBOX_ARTICLES = 20         # max number of recently saved articles to sync
MAX_HTML_CHARS = 300_000        # max characters per article (longer articles are truncated)
```

After editing, commit and push to your repo for the changes to take effect.

---

## Article Sync Rules

Each day's sync pulls from two sources, then deduplicates by article ID:

| Source | Rule |
|--------|------|
| Articles tagged `remarkable` | All synced, no limit |
| Recently saved (new/later) | Up to 20 articles total |

> **Note:** Only articles you actively saved to Readwise Reader have full content. RSS feed articles only store a title and summary — the full text cannot be synced.

---

## FAQ

**Q: The workflow failed with a 403 error.**
The most common cause is a malformed `GOOGLE_OAUTH_CREDENTIALS` secret. Make sure you copied the complete JSON including the outer `{` and `}`, with no truncated lines or extra whitespace.

**Q: New articles aren't showing up on rM2.**
Make sure your rM2 is connected to Wi-Fi. Google Drive sync requires an internet connection and may take a few minutes.

**Q: Articles only show the title, no content.**
The article came from an RSS feed and Readwise didn't store the full text. Re-save it using the "Save to Readwise Reader" method, then wait for the next sync.

**Q: The workflow failed with `invalid_grant: Token has been expired or revoked`.**
The OAuth app is still in test mode. Test-mode refresh tokens expire after 7 days. To fix:
1. Google Cloud Console → OAuth consent screen → **Audience** → Publishing Status → **Publish App**
2. Re-run `get_token.py` to obtain a new refresh token
3. Go to GitHub Repo → Settings → Secrets → update `GOOGLE_OAUTH_CREDENTIALS`

**Q: Can I change the schedule?**
Yes. Edit the cron expression in `.github/workflows/sync.yml`. The current value `30 16 * * *` means UTC 16:30, which is 00:30 Taiwan time (UTC+8).

---

## Credential Security

This project uses three sensitive credentials: the Readwise API Token, Google OAuth credentials, and the Google Drive folder ID.

**✅ Do**
- Store all credentials only in **GitHub Secrets**, injected at runtime via `${{ secrets.xxx }}`
- Delete `client_secret_xxx.json` after use, or keep it outside the repo folder
- `.gitignore` already blocks `client_secret*.json`, `credentials*.json`, `.env`, etc. to prevent accidental commits

**❌ Don't**
- Hardcode tokens or JSON content directly in `sync.py` or any source file
- Paste tokens or JSON into chats, forums, GitHub Issues, or PR comments
- Place `client_secret_xxx.json` inside the repo folder and then run `git add .`

**If a credential is accidentally exposed**
- **Readwise Token**: Go to [readwise.io/access_token](https://readwise.io/access_token) and regenerate it
- **Google OAuth credentials**: Go to Google Cloud Console → Credentials → delete and recreate the OAuth client, then re-run `get_token.py`
- Update GitHub Secrets immediately with the new credentials

---

## Technical Stack

| Component | Details |
|-----------|---------|
| Runtime | GitHub Actions (free) |
| Language | Python 3.11 |
| File format | EPUB |
| EPUB generation | `ebooklib` |
| Google Drive | `google-api-python-client` |
| Google auth | OAuth2 refresh token |
| Schedule | GitHub Actions cron (daily at UTC 16:30) |

---

## Project Structure

```
readwise-remarkable-sync/
├── sync.py                      # Main script: fetch articles, convert to EPUB, upload to Drive
├── get_token.py                 # One-time helper: generate a Google OAuth refresh token locally
├── requirements.txt             # Python dependencies
├── .github/
│   └── workflows/
│       └── sync.yml             # GitHub Actions schedule (triggers sync.py daily at UTC 16:30)
├── CLAUDE.md                    # Claude Code project notes (AI dev tooling, not business logic)
├── .gitignore                   # Excludes OAuth credentials, .env files, Python cache
├── README.md                    # This file (English)
└── README.zh-TW.md              # Traditional Chinese version
```

### File relationships

```
.github/workflows/sync.yml          ← schedule trigger
    └─ runs sync.py                 ← main script (all business logic lives here)
            ├─ READWISE_TOKEN        ┐
            ├─ GDRIVE_FOLDER_ID      ├─ read from GitHub Secrets at runtime
            └─ GOOGLE_OAUTH_CREDS   ┘

get_token.py                        ← run locally once during initial setup
    └─ outputs GOOGLE_OAUTH_CREDENTIALS JSON → paste into GitHub Secret
```

`get_token.py` is only needed during **initial setup** — the daily sync does not depend on it.

### sync.py function reference

| Function | Purpose |
|----------|---------|
| `readwise_get()` | Generic Readwise API GET with automatic 429 retry |
| `fetch_tagged_articles()` | Fetch all articles tagged `remarkable` (auto-paginated) |
| `fetch_recent_articles()` | Fetch the latest new/later articles (10 per location, 20 total max) |
| `merge_articles()` | Merge both sources and deduplicate by article ID |
| `fetch_full_html()` | Re-fetch a single article's full HTML by ID (`withHtmlContent=true`) |
| `article_to_epub()` | Convert an article to an EPUB and return a `BytesIO` |
| `get_gdrive_service()` | Build a Google Drive API client using OAuth2 refresh token |
| `list_drive_files()` | List all files in a Drive folder (paginated via nextPageToken) |
| `delete_files()` | Delete a given list of Drive files |
| `upload_epub()` | Upload an EPUB to the Drive folder |
| `main()` | Orchestrates: record old files → upload new → delete old only if upload succeeded |
