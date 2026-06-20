"""
Readwise Reader → reMarkable 2 Sync Script
每日同步文章到 Google Drive，由 rM2 原生整合自動拉取

文章來源：
  1. 標記 'remarkable' tag 的文章（全部）
  2. 最新儲存到 new/later 的文章（最多 20 篇，Readwise 有解析完整內文）
"""

import os
import re
import json
import io
import logging
import time
from datetime import datetime, timezone

import requests
from ebooklib import epub
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# ── 環境變數 ──────────────────────────────────────────────
READWISE_TOKEN = os.environ['READWISE_TOKEN']
GDRIVE_FOLDER_ID = os.environ['GDRIVE_FOLDER_ID']

REMARKABLE_TAG = 'remarkable'
MAX_INBOX_ARTICLES = 20
MAX_HTML_CHARS = 300_000   # ~300KB，超過截斷，避免記憶體爆量
API_DELAY = 3              # 秒，Readwise list API 限速 20/min，間隔 3s 安全邊際
READWISE_API = 'https://readwise.io/api/v3/list/'


# ── Readwise Reader ───────────────────────────────────────

def readwise_get(params, with_html=False):
    """Readwise API GET，遇到 429 自動等待重試。
    with_html=True 才帶 withHtmlContent=true（只在單篇抓取時用，避免 list 回應過大）"""
    headers = {'Authorization': f'Token {READWISE_TOKEN}'}
    merged = dict(params)
    if with_html:
        merged['withHtmlContent'] = 'true'
    for attempt in range(5):
        resp = requests.get(READWISE_API, headers=headers, params=merged)
        if resp.status_code == 429:
            wait = int(resp.headers.get('Retry-After', 10)) + 1
            logger.warning(f"Rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("Readwise API rate limit exceeded after retries")


def fetch_tagged_articles():
    """抓取標記 'remarkable' tag 的文章。
    直接用 API tag 參數過濾，不需掃描所有 location。"""
    articles = []
    params = {'tag': REMARKABLE_TAG}
    while True:
        data = readwise_get(params)
        articles.extend(data.get('results', []))
        next_cursor = data.get('nextPageCursor')
        if not next_cursor:
            break
        params['pageCursor'] = next_cursor
        time.sleep(API_DELAY)

    time.sleep(API_DELAY)  # 最後一頁結束後也間隔，確保與下一個 API call 有 3s 緩衝
    logger.info(f"Tagged articles: {len(articles)}")
    return articles


def fetch_recent_articles():
    """抓取最新儲存到 new/later 的文章（各取前 20 篇，合併去重）。
    這些 location 的文章 Readwise 已解析完整 HTML，feed 文章則無。"""
    seen = {}
    for location in ('new', 'later'):
        data = readwise_get({'location': location, 'limit': MAX_INBOX_ARTICLES // 2})
        for doc in data.get('results', []):
            seen[doc['id']] = doc
        time.sleep(API_DELAY)  # 兩個 location 之間加間隔

    articles = list(seen.values())  # 各 location 已各限 MAX_INBOX_ARTICLES//2 篇，不需再裁
    logger.info(f"Recent saved articles (new/later, max {MAX_INBOX_ARTICLES}): {len(articles)}")
    return articles


def merge_articles(tagged, inbox):
    """合併並去重（以文章 ID 為 key）"""
    seen = {}
    for article in tagged + inbox:
        seen[article['id']] = article
    return list(seen.values())


# ── 格式轉換 ──────────────────────────────────────────────

def sanitize_filename(title):
    """將文章標題轉為合法的檔名"""
    name = re.sub(r'[^\w\s\-]', '', title)
    name = re.sub(r'\s+', '_', name.strip())
    return (name[:60] if name else 'untitled') + '.epub'


def fetch_full_html(doc_id):
    """以 ID 單獨抓取文章，取回 Readwise 解析後的完整 HTML（withHtmlContent=true）"""
    data = readwise_get({'id': doc_id}, with_html=True)
    results = data.get('results', [])
    if results:
        html = results[0].get('html_content') or results[0].get('html') or ''
        logger.info(f"  Single-fetch html_content length: {len(html)} chars")
        return html
    return ''


def article_to_epub(article):
    """將文章轉換成 EPUB，回傳 BytesIO"""
    book = epub.EpubBook()
    book.set_identifier(str(article['id']))
    book.set_title(article.get('title', 'Untitled'))
    book.set_language('en')

    if article.get('author'):
        book.add_author(article['author'])

    # 文章內文：優先用 html_content（需 withHtmlContent=true 才回傳），其次 html
    html_content = article.get('html_content') or article.get('html') or ''
    logger.info(f"  html_content length: {len(html_content)} chars, summary length: {len(article.get('summary') or '')} chars")

    if not html_content or len(html_content.strip()) < 200:
        # 仍為空，以 ID 單獨再抓一次（含 withHtmlContent=true）
        logger.info(f"  html_content empty, fetching full content by ID...")
        html_content = fetch_full_html(article['id'])
        # 注意：delay 由 main loop 統一控制，不在這裡 sleep

    # 超過大小上限則截斷，避免記憶體爆量（書籍、長文等）
    if len(html_content) > MAX_HTML_CHARS:
        logger.warning(f"  html_content too large ({len(html_content)} chars), truncating to {MAX_HTML_CHARS}")
        html_content = html_content[:MAX_HTML_CHARS]

    if not html_content or len(html_content.strip()) < 200:
        logger.warning(f"  No HTML available from Readwise, falling back to summary")
        summary = article.get('summary') or ''
        source_url = article.get('source_url') or article.get('url') or ''
        html_content = (
            f"<p>{summary}</p><hr/>"
            f'<p><a href="{source_url}">前往原始文章閱讀完整內容</a></p>'
        ) if summary else (
            f"<p>內文無法取得，請至原始來源閱讀：</p>"
            f'<p><a href="{source_url}">{source_url}</a></p>'
        )

    # 加上文章標頭資訊
    header = f"<h1>{article.get('title', 'Untitled')}</h1>"
    if article.get('author'):
        header += f"<p><em>{article['author']}</em></p>"
    if article.get('source_url'):
        header += f"<p><small>{article['source_url']}</small></p>"
    header += "<hr/>"

    chapter = epub.EpubHtml(
        title=article.get('title', 'Untitled'),
        file_name='article.xhtml',
        lang='en'
    )
    # ebooklib 內部用 lxml 解析 content。
    # Readwise 的 html_content 是 HTML（非 XML），加嚴格 XML 宣告或 XHTML namespace
    # 會讓 lxml 解析失敗，拋出 "Document is empty"。
    # 保持簡單的 <html><body> 格式，ebooklib 能正常處理。
    chapter.content = f'<html><body>{header}{html_content}</body></html>'

    book.add_item(chapter)
    book.toc = [chapter]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    # chapter 放第一位：rM2 打開 EPUB 直接顯示內文，不是目錄頁
    # nav 仍保留在 spine（EPUB3 合規），但排在 chapter 之後
    book.spine = [chapter, 'nav']

    buffer = io.BytesIO()
    epub.write_epub(buffer, book)
    buffer.seek(0)
    return buffer


# ── Google Drive ──────────────────────────────────────────

def get_gdrive_service():
    """建立 Google Drive service（使用 OAuth2 refresh token）"""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds_data = json.loads(os.environ['GOOGLE_OAUTH_CREDENTIALS'])
    creds = Credentials(
        token=creds_data.get('token'),
        refresh_token=creds_data['refresh_token'],
        token_uri=creds_data['token_uri'],
        client_id=creds_data['client_id'],
        client_secret=creds_data['client_secret'],
        scopes=creds_data['scopes']
    )
    if not creds.valid:
        creds.refresh(Request())
    return build('drive', 'v3', credentials=creds)


def list_drive_files(service, folder_id):
    """列出資料夾內所有檔案（含分頁，避免 pageSize=100 截斷）"""
    files = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields='nextPageToken, files(id, name)',
            pageToken=page_token
        ).execute()
        files.extend(resp.get('files', []))
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    return files


def delete_files(service, files):
    """刪除指定的 Drive 檔案清單"""
    for f in files:
        service.files().delete(fileId=f['id']).execute()
        logger.info(f"Deleted: {f['name']}")
    logger.info(f"Cleaned up {len(files)} old files")


def upload_epub(service, filename, epub_buffer, folder_id):
    """上傳 EPUB 到 Google Drive 資料夾"""
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    media = MediaIoBaseUpload(
        epub_buffer,
        mimetype='application/epub+zip',
        resumable=False
    )
    result = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name'
    ).execute()
    logger.info(f"Uploaded: {result['name']}")


# ── 主程式 ────────────────────────────────────────────────

def main():
    logger.info("=== Readwise → reMarkable sync started ===")

    # 建立 Google Drive 連線
    service = get_gdrive_service()

    # 先記錄舊檔案，等新檔案上傳成功後再刪（避免失敗時 Drive 資料夾變空）
    old_files = list_drive_files(service, GDRIVE_FOLDER_ID)
    logger.info(f"Found {len(old_files)} existing files to replace after upload")

    # 抓取文章
    tagged = fetch_tagged_articles()
    recent = fetch_recent_articles()
    articles = merge_articles(tagged, recent)
    logger.info(f"Total articles to sync: {len(articles)}")

    if not articles:
        logger.info("No articles to sync. Done.")
        return

    # 逐篇轉換並上傳，每篇之間統一等待 API_DELAY 秒
    success = 0
    for i, article in enumerate(articles):
        title = article.get('title', f"article_{article['id']}")
        try:
            epub_buffer = article_to_epub(article)
            filename = sanitize_filename(title)
            upload_epub(service, filename, epub_buffer, GDRIVE_FOLDER_ID)
            success += 1
        except Exception as e:
            logger.error(f"Failed: '{title}' — {e}")
        # 每篇之間間隔，避免 Readwise API 限速（最後一篇不需要）
        if i < len(articles) - 1:
            time.sleep(API_DELAY)

    # 至少一篇上傳成功才刪舊檔案，確保 Drive 資料夾不會變空
    if success > 0:
        delete_files(service, old_files)
    else:
        logger.warning("No articles uploaded successfully — keeping existing files intact")

    logger.info(f"=== Done: {success}/{len(articles)} articles synced ===")


if __name__ == '__main__':
    main()
