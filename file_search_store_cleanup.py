#!/usr/bin/env python3
"""
File Search Store Cleanup Tool

Deletes all documents from a specified Gemini File Search Store using OAuth authentication.

Usage:
    python file_search_store_cleanup.py <store_id> [--dry-run] [--force]

Arguments:
    store_id    The File Search Store ID (e.g., fileSearchStores/mystore-abc123)

Options:
    --dry-run   List files without deleting
    --force     Skip confirmation prompt
    --verbose   Enable debug logging

Environment Variables (in .env):
    TOKEN_FILE        - Path to OAuth token cache
    CREDENTIALS_FILE  - Path to OAuth credentials JSON
"""

import os
import sys
import pickle
import logging
import argparse
from datetime import datetime
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google import genai

# === CONFIGURATION ===
ENV_FILE_PATH = r'.//.env'

# OAuth2 scopes for Gemini File Search
SCOPES = [
    'https://www.googleapis.com/auth/generative-language.retriever',
    'https://www.googleapis.com/auth/cloud-platform'
]

# Global logger
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Delete all documents from a Gemini File Search Store'
    )
    parser.add_argument(
        'store_id',
        help='File Search Store ID (e.g., fileSearchStores/mystore-abc123)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='List files without deleting'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable debug logging'
    )
    return parser.parse_args()


def setup_logging(verbose=False):
    """Configure logging with console and file handlers."""
    log_level = logging.DEBUG if verbose else logging.INFO

    # Create logs directory
    log_dir = os.path.join(os.path.dirname(ENV_FILE_PATH), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f'cleanup_{datetime.now():%Y%m%d}.log')

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return logging.getLogger(__name__)


def get_oauth_credentials():
    """Get valid OAuth2 credentials from storage or run OAuth flow."""
    token_file = os.getenv('TOKEN_FILE', r'C:\Users\acgar\OneDrive\Documents\GoogleAI\token.pickle')
    credentials_file = os.getenv('CREDENTIALS_FILE', r'C:\Users\acgar\OneDrive\Documents\GoogleAI\credentials.json')

    creds = None

    if os.path.exists(token_file):
        with open(token_file, 'rb') as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info('Refreshing expired OAuth token...')
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                logger.error(f'Credentials file not found: {credentials_file}')
                return None

            logger.info('Starting OAuth2 flow (browser will open)...')
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, 'wb') as f:
            pickle.dump(creds, f)
            logger.info(f'Credentials saved to {token_file}')

    return creds


def get_file_info(doc):
    """Extract document information."""
    full_name = getattr(doc, 'name', 'Unknown')
    doc_id = full_name.split('/')[-1] if '/' in full_name else full_name
    display_name = getattr(doc, 'display_name', None) or doc_id
    state = getattr(doc, 'state', 'Unknown')

    return {
        'full_name': full_name,
        'doc_id': doc_id,
        'display_name': display_name,
        'state': str(state)
    }


def delete_document_with_force(api_key, doc_name):
    """Delete a document using REST API with force=true to handle non-empty documents."""
    # REST API endpoint: DELETE https://generativelanguage.googleapis.com/v1beta/{name}?force=true
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    url = f"{base_url}/{doc_name}?force=true&key={api_key}"

    response = requests.delete(url)

    if response.status_code == 200:
        return True, None
    else:
        return False, response.text


def confirm_deletion(store_id, file_count):
    """Ask user to confirm deletion."""
    print('\n' + '!' * 60)
    print('WARNING: This will DELETE ALL DOCUMENTS from:')
    print(f'  Store: {store_id}')
    print(f'  Total documents: {file_count}')
    print('!' * 60)

    response = input('\nType "DELETE ALL" to confirm (or anything else to cancel): ')
    return response == "DELETE ALL"


def main():
    """Main entry point."""
    global logger

    # Load environment
    if os.path.exists(ENV_FILE_PATH):
        load_dotenv(ENV_FILE_PATH)

    # Parse arguments
    args = parse_arguments()

    # Setup logging
    logger = setup_logging(args.verbose)

    store_id = args.store_id

    # Ensure store_id has correct prefix
    if not store_id.startswith('fileSearchStores/'):
        store_id = f'fileSearchStores/{store_id}'

    mode_str = '(DRY RUN)' if args.dry_run else ''
    logger.info(f'File Search Store Cleanup {mode_str}')
    logger.info('=' * 60)
    logger.info(f'Target Store: {store_id}')

    # Authenticate with OAuth
    logger.info('[1/4] Authenticating with OAuth2...')
    creds = get_oauth_credentials()
    if not creds:
        logger.error('Authentication failed')
        return 1
    logger.info('OAuth authentication successful')

    # Initialize Gemini client with OAuth credentials
    logger.info('[2/4] Initializing Gemini client...')
    try:
        # Use API key from env as fallback (Gemini SDK preference)
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            genai_client = genai.Client(api_key=api_key)
        else:
            # Try OAuth token (may not work with all Gemini endpoints)
            genai_client = genai.Client(api_key=creds.token)
        logger.info('Gemini client initialized')
    except Exception as e:
        logger.error(f'Failed to initialize Gemini client: {e}')
        return 1

    # List documents
    logger.info('[3/4] Listing documents in store...')
    try:
        response = genai_client.file_search_stores.documents.list(parent=store_id)
        documents = list(response)
    except Exception as e:
        logger.error(f'Failed to list documents: {e}')
        return 1

    if not documents:
        logger.info('No documents found. Store is empty.')
        return 0

    logger.info(f'Found {len(documents)} document(s)')

    # Display documents
    print('\n' + '-' * 90)
    print(f'{"#":<4} {"Display Name":<40} {"Document ID":<30} {"State":<12}')
    print('-' * 90)

    for i, doc in enumerate(documents, 1):
        info = get_file_info(doc)
        display = info["display_name"][:38] + '..' if len(info["display_name"]) > 40 else info["display_name"]
        doc_id = info["doc_id"][:28] + '..' if len(info["doc_id"]) > 30 else info["doc_id"]
        print(f'{i:<4} {display:<40} {doc_id:<30} {info["state"]:<12}')

    print('-' * 90)
    print(f'Total: {len(documents)} document(s)\n')

    # Dry run - stop here
    if args.dry_run:
        logger.info('[DRY-RUN] Would delete all documents listed above')
        return 0

    # Confirm deletion
    if not args.force:
        if not confirm_deletion(store_id, len(documents)):
            logger.info('Deletion cancelled by user')
            return 0

    # Delete documents
    logger.info('[4/4] Deleting documents...')

    deleted = 0
    failed = 0

    api_key = os.getenv('GEMINI_API_KEY')

    for i, doc in enumerate(documents, 1):
        info = get_file_info(doc)

        success, error = delete_document_with_force(api_key, info['full_name'])

        if success:
            deleted += 1
            logger.info(f'[{i}/{len(documents)}] Deleted: {info["display_name"]} (ID: {info["doc_id"]})')
        else:
            failed += 1
            logger.error(f'[{i}/{len(documents)}] Failed: {info["display_name"]} - {error}')

    # Summary
    logger.info('=' * 60)
    logger.info('=== Cleanup Summary ===')
    logger.info(f'Documents deleted: {deleted}')
    logger.info(f'Documents failed: {failed}')
    logger.info(f'Store: {store_id}')

    if failed > 0:
        logger.warning('Completed with errors')
        return 1

    logger.info('Cleanup completed successfully')
    return 0


if __name__ == '__main__':
    sys.exit(main())
