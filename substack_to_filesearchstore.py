#!/usr/bin/env python3
"""
Substack to Gemini File Search Store Sync

Fetches ALL posts from a Substack blog (via the archive API) and uploads
each as a separate text document to a Gemini File Search Store. Skips
posts that have already been uploaded (matched by display name).

On the first run, creates a new File Search Store and saves the ID to .env.
Subsequent runs reuse the same store.

Usage:
    python substack_to_filesearchstore.py-
"""

import os
import sys
import tempfile

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

# === CONFIGURATION ===
ENV_FILE_PATH = r'.//.env'
STORE_DISPLAY_NAME = 'SubstackBlog'


def get_or_create_store(client):
    """Return the File Search Store ID, creating one if needed."""
    store_id = os.getenv('SUBSTACK_STORE_ID')

    if store_id:
        print(f'Using existing store: {store_id}')
        return store_id

    # Create a new store
    print(f'Creating new File Search Store "{STORE_DISPLAY_NAME}"...')
    store = client.file_search_stores.create(
        config={'display_name': STORE_DISPLAY_NAME}
    )
    store_id = store.name
    print(f'Created store: {store_id}')

    # Persist the store ID to .env for future runs
    with open(ENV_FILE_PATH, 'a', encoding='utf-8') as f:
        f.write(f'\nSUBSTACK_STORE_ID={store_id}\n')
    print(f'Saved SUBSTACK_STORE_ID to .env')

    return store_id


def get_existing_documents(client, store_id):
    """Return a set of display names already in the store."""
    existing = set()
    try:
        documents = client.file_search_stores.documents.list(parent=store_id)
        for doc in documents:
            if doc.display_name:
                existing.add(doc.display_name)
    except Exception as e:
        print(f'Warning: Could not list existing documents: {e}')
    return existing


def fetch_substack_posts(base_url):
    """Fetch ALL posts via /api/v1/posts (includes posts the archive endpoint misses)."""
    api_url = f'{base_url}/api/v1/posts'
    all_posts = []
    offset = 0
    limit = 50

    print(f'Fetching posts from {base_url}...')

    while True:
        resp = requests.get(api_url, params={'limit': limit, 'offset': offset})
        resp.raise_for_status()
        batch = resp.json()

        if not batch:
            break

        all_posts.extend(batch)
        if len(batch) < limit:
            break
        offset += limit

    print(f'Found {len(all_posts)} post(s)')
    return all_posts


def fetch_post_content(base_url, slug):
    """Fetch the full HTML body for a single post by slug."""
    resp = requests.get(f'{base_url}/api/v1/posts/{slug}')
    resp.raise_for_status()
    post = resp.json()
    return post.get('body_html', '') or ''


def html_to_text(html_content):
    """Convert HTML to clean plain text."""
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator='\n', strip=True)


def make_display_name(title):
    """Build a display name for a post (prefixed to avoid collisions)."""
    return f'substack - {title.strip()}'


def upload_post(client, store_id, title, text_content):
    """Upload a single post as a .txt file to the File Search Store."""
    display_name = make_display_name(title)
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix='.txt', mode='w', encoding='utf-8'
        ) as tmp:
            tmp.write(f'{title}\n{"=" * len(title)}\n\n')
            tmp.write(text_content)
            tmp_path = tmp.name

        client.file_search_stores.upload_to_file_search_store(
            file=tmp_path,
            file_search_store_name=store_id,
            config={'display_name': display_name},
        )
        return True

    except Exception as e:
        print(f'  Error uploading "{title}": {e}')
        return False

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def main():
    # Load environment
    load_dotenv(ENV_FILE_PATH)

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print('Error: GEMINI_API_KEY not found in .env')
        sys.exit(1)

    substack_url = os.getenv('SUBSTACK_URL')
    if not substack_url:
        print('Error: SUBSTACK_URL not found in .env')
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Get or create the store
    store_id = get_or_create_store(client)

    # List existing documents for deduplication
    print('Checking for already-uploaded posts...')
    existing_names = get_existing_documents(client, store_id)
    if existing_names:
        print(f'  {len(existing_names)} document(s) already in store')

    # Fetch posts from Substack
    posts = fetch_substack_posts(substack_url)

    uploaded = 0
    skipped = 0
    failed = 0

    for post in posts:
        title = post.get('title', 'Untitled')
        slug = post.get('slug', '')
        display_name = make_display_name(title)

        if display_name in existing_names:
            print(f'  SKIP (already uploaded): {title}')
            skipped += 1
            continue

        # Fetch full post content by slug
        html = fetch_post_content(substack_url, slug) if slug else ''

        if not html:
            print(f'  SKIP (no content): {title}')
            skipped += 1
            continue

        text = html_to_text(html)
        print(f'  UPLOAD: {title} ({len(text)} chars)')

        if upload_post(client, store_id, title, text):
            uploaded += 1
        else:
            failed += 1

    # Summary
    print()
    print('=' * 50)
    print(f'  Posts found:    {len(posts)}')
    print(f'  Uploaded:       {uploaded}')
    print(f'  Skipped:        {skipped}')
    print(f'  Failed:         {failed}')
    print('=' * 50)


if __name__ == '__main__':
    main()
