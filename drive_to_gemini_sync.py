#!/usr/bin/env python3
"""
Google Drive to Gemini File Search Store Sync Script

Polls a Google Drive folder and uploads files to Gemini File Search Store,
then moves processed files to a separate folder.

Usage:
    python drive_to_gemini_sync.py [--dry-run] [--verbose]

Environment Variables (in .env):
    SOURCE_FOLDER_ID      - Google Drive folder to poll
    PROCESSED_FOLDER_ID   - Destination for processed files
    FILE_SEARCH_STORE_ID  - Gemini File Search Store ID
    GEMINI_API_KEY        - API key for Gemini
    TOKEN_FILE            - Path to OAuth token cache
    CREDENTIALS_FILE      - Path to OAuth credentials JSON
"""

import os
import io
import sys
import pickle
import logging
import argparse
import tempfile
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google import genai

# === CONFIGURATION ===
ENV_FILE_PATH = r'.env'

# OAuth2 scopes - full drive access needed for move operations
SCOPES = ['https://www.googleapis.com/auth/drive']

# Supported file types for Gemini File Search Store
SUPPORTED_MIME_TYPES = {
    'application/pdf': '.pdf',
    'text/plain': '.txt',
    'text/html': '.html',
    'text/csv': '.csv',
    'application/vnd.google-apps.document': '.gdoc',  # Export as PDF
    'application/vnd.google-apps.spreadsheet': '.gsheet',  # Export as CSV
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
}

# Global logger
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Sync Google Drive files to Gemini File Search Store'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='List files that would be processed without making changes'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose/debug logging'
    )
    return parser.parse_args()


def setup_logging(verbose=False):
    """Configure logging with console and file handlers."""
    log_level = logging.DEBUG if verbose else logging.INFO

    # Create logs directory if needed
    log_dir = os.path.join(os.path.dirname(ENV_FILE_PATH), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Log filename with date
    log_file = os.path.join(log_dir, f'sync_{datetime.now():%Y%m%d}.log')

    # Format: timestamp - level - message
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # File handler (rotating, max 10MB, keep 7 files)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # Always verbose in file
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return logging.getLogger(__name__)


def validate_env_variables():
    """Validate that all required environment variables are set."""
    required_vars = {
        'SOURCE_FOLDER_ID': os.getenv('SOURCE_FOLDER_ID'),
        'PROCESSED_FOLDER_ID': os.getenv('PROCESSED_FOLDER_ID'),
        'FILE_SEARCH_STORE_ID': os.getenv('FILE_SEARCH_STORE_ID'),
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
        'TOKEN_FILE': os.getenv('TOKEN_FILE'),
        'CREDENTIALS_FILE': os.getenv('CREDENTIALS_FILE'),
    }

    missing_vars = [var for var, value in required_vars.items() if not value]

    if missing_vars:
        logger.error(f'Missing required environment variables: {missing_vars}')
        return False

    # Check that credentials file exists
    creds_file = os.getenv('CREDENTIALS_FILE')
    if not os.path.exists(creds_file):
        logger.error(f'Credentials file not found: {creds_file}')
        return False

    return True


def get_credentials():
    """Get valid OAuth2 credentials from storage or run OAuth flow."""
    creds = None
    token_file = os.getenv('TOKEN_FILE')
    credentials_file = os.getenv('CREDENTIALS_FILE')

    if os.path.exists(token_file):
        with open(token_file, 'rb') as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info('Refreshing expired OAuth token...')
            creds.refresh(Request())
        else:
            logger.info('Starting OAuth2 flow (browser will open)...')
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_file, 'wb') as f:
            pickle.dump(creds, f)
            logger.info(f'Credentials saved to {token_file}')

    return creds


def list_files_in_folder(drive_service, folder_id):
    """List all files (not folders) in a Google Drive folder."""
    query = f"'{folder_id}' in parents and trashed=false and mimeType != 'application/vnd.google-apps.folder'"

    files = []
    page_token = None

    while True:
        results = drive_service.files().list(
            q=query,
            fields='nextPageToken, files(id, name, mimeType, size, createdTime)',
            pageSize=100,
            pageToken=page_token
        ).execute()

        files.extend(results.get('files', []))
        page_token = results.get('nextPageToken')

        if not page_token:
            break

    logger.info(f'Found {len(files)} file(s) in source folder')
    return files


def is_supported_file_type(file):
    """Check if file type is supported by Gemini File Search Store."""
    mime_type = file.get('mimeType', '')
    return mime_type in SUPPORTED_MIME_TYPES


def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes is None:
        return 'unknown size'
    size = int(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f'{size:.1f} {unit}'
        size /= 1024
    return f'{size:.1f} TB'


def download_file(drive_service, file_id, mime_type, filename):
    """
    Download file content from Google Drive.

    Handles Google Workspace files by exporting to compatible format.

    Returns:
        tuple: (file_content_bytes, final_filename) or (None, None) on error
    """
    try:
        export_extension = None

        if mime_type == 'application/vnd.google-apps.document':
            # Export Google Doc as PDF
            logger.debug(f'Exporting Google Doc as PDF: {filename}')
            request = drive_service.files().export_media(
                fileId=file_id, mimeType='application/pdf'
            )
            export_extension = '.pdf'
        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            # Export Google Sheet as CSV
            logger.debug(f'Exporting Google Sheet as CSV: {filename}')
            request = drive_service.files().export_media(
                fileId=file_id, mimeType='text/csv'
            )
            export_extension = '.csv'
        else:
            # Regular file - download directly
            request = drive_service.files().get_media(fileId=file_id)

        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                logger.debug(f'Download progress: {int(status.progress() * 100)}%')

        file_stream.seek(0)
        content = file_stream.read()

        # Adjust filename for exported files
        final_filename = filename
        if export_extension:
            base_name = os.path.splitext(filename)[0]
            final_filename = base_name + export_extension

        return content, final_filename

    except Exception as e:
        logger.error(f'Failed to download {filename}: {e}')
        return None, None


def upload_to_file_search_store(genai_client, file_content, filename, store_id, timeout_seconds=300):
    """
    Upload file to Gemini File Search Store.

    Args:
        genai_client: Initialized genai.Client
        file_content: File bytes
        filename: Original filename
        store_id: File Search Store ID
        timeout_seconds: Max wait time for processing

    Returns:
        bool: True if upload succeeded
    """
    tmp_path = None
    try:
        # Get file extension
        _, ext = os.path.splitext(filename)
        if not ext:
            ext = '.bin'

        # Write to temp file (Gemini SDK requires file path)
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        logger.info(f'Uploading {filename} to File Search Store...')

        # Upload to Gemini File Search Store
        genai_client.file_search_stores.upload_to_file_search_store(
            file=tmp_path,
            file_search_store_name=store_id
        )

        logger.info(f'Successfully uploaded {filename} to File Search Store')
        return True

    except Exception as e:
        logger.error(f'Failed to upload {filename} to File Search Store: {e}')
        return False

    finally:
        # Cleanup temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def move_file_to_folder(drive_service, file_id, filename, source_folder_id, dest_folder_id):
    """Move a file from source folder to destination folder."""
    try:
        drive_service.files().update(
            fileId=file_id,
            addParents=dest_folder_id,
            removeParents=source_folder_id,
            fields='id, parents'
        ).execute()

        logger.info(f'Moved {filename} to processed folder')
        return True

    except Exception as e:
        logger.error(f'Failed to move {filename}: {e}')
        return False


def process_file(drive_service, genai_client, file, source_folder_id, processed_folder_id, store_id, dry_run=False):
    """
    Process a single file: download, upload to Gemini, move to processed.

    Returns:
        str: 'processed', 'skipped', or 'failed'
    """
    filename = file['name']
    mime_type = file.get('mimeType', '')
    file_size = format_file_size(file.get('size'))

    # Check if file type is supported
    if not is_supported_file_type(file):
        logger.warning(f'Skipping unsupported file: {filename} ({mime_type})')
        return 'skipped'

    logger.info(f'Processing: {filename} ({file_size})')

    if dry_run:
        logger.info(f'[DRY-RUN] Would process: {filename}')
        return 'processed'

    # Step 1: Download from Drive
    content, final_filename = download_file(drive_service, file['id'], mime_type, filename)
    if content is None:
        return 'failed'

    # Step 2: Upload to Gemini File Search Store
    success = upload_to_file_search_store(genai_client, content, final_filename, store_id)
    if not success:
        return 'failed'

    # Step 3: Move to processed folder
    moved = move_file_to_folder(
        drive_service, file['id'], filename,
        source_folder_id, processed_folder_id
    )
    if not moved:
        # File was uploaded but not moved - log warning but count as processed
        logger.warning(f'File {filename} uploaded but could not be moved to processed folder')

    return 'processed'


def log_summary(stats, dry_run=False):
    """Log the sync summary."""
    logger.info('=' * 50)
    if dry_run:
        logger.info('=== Dry Run Summary ===')
        logger.info(f'Files would be processed: {stats["processed"]}')
        logger.info(f'Files would be skipped: {stats["skipped"]}')
    else:
        logger.info('=== Sync Summary ===')
        logger.info(f'Files found: {stats["found"]}')
        logger.info(f'Files processed: {stats["processed"]}')
        logger.info(f'Files skipped: {stats["skipped"]}')
        logger.info(f'Files failed: {stats["failed"]}')

    if stats['failed'] > 0:
        logger.warning('Sync completed with errors')
    else:
        logger.info('Sync completed successfully')
    logger.info('=' * 50)


def main():
    """Main entry point."""
    global logger

    # Load environment variables
    if not os.path.exists(ENV_FILE_PATH):
        print(f'Error: .env file not found at: {ENV_FILE_PATH}')
        return 1

    load_dotenv(ENV_FILE_PATH)

    # Parse arguments
    args = parse_arguments()

    # Setup logging
    logger = setup_logging(args.verbose)

    mode_str = '(DRY RUN)' if args.dry_run else ''
    logger.info(f'Starting Google Drive to Gemini sync {mode_str}')

    # [1/5] Validate configuration
    logger.info('[1/5] Validating configuration...')
    if not validate_env_variables():
        return 1
    logger.info('Configuration validated successfully')

    # Get config values
    source_folder_id = os.getenv('SOURCE_FOLDER_ID')
    processed_folder_id = os.getenv('PROCESSED_FOLDER_ID')
    store_id = os.getenv('FILE_SEARCH_STORE_ID')
    gemini_api_key = os.getenv('GEMINI_API_KEY')

    # [2/5] Authenticate
    logger.info('[2/5] Authenticating with OAuth2...')
    try:
        creds = get_credentials()
        logger.info('OAuth authentication successful')
    except Exception as e:
        logger.error(f'Authentication failed: {e}')
        return 1

    # [3/5] Build services
    logger.info('[3/5] Building service clients...')
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        genai_client = genai.Client(api_key=gemini_api_key)
        logger.info('Services initialized')
    except Exception as e:
        logger.error(f'Failed to initialize services: {e}')
        return 1

    # [4/5] Process files
    logger.info('[4/5] Processing files...')

    # List files in source folder
    try:
        files = list_files_in_folder(drive_service, source_folder_id)
    except Exception as e:
        logger.error(f'Failed to list files in source folder: {e}')
        return 1

    if not files:
        logger.info('No files to process')
        return 0

    # Process each file
    stats = {'found': len(files), 'processed': 0, 'skipped': 0, 'failed': 0}

    for file in files:
        result = process_file(
            drive_service, genai_client, file,
            source_folder_id, processed_folder_id, store_id,
            dry_run=args.dry_run
        )
        stats[result] += 1

    # [5/5] Summary
    logger.info('[5/5] Generating summary...')
    log_summary(stats, args.dry_run)

    return 0 if stats['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

