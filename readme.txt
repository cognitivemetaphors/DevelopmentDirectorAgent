
gmail_savepdfs_to_gdrive.py
===========================

Extracts PDF attachments from Gmail emails and uploads them to Google Drive.
Searches for unread emails from a specific sender with a specific subject,
extracts PDFs, uploads to Drive, and labels processed emails.

USAGE:
    python gmail_savepdfs_to_gdrive.py

ENVIRONMENT (.env):
    SENDER_EMAIL      - Email address to filter by (e.g., sender@example.com)
    SUBJECT_KEYWORD   - Subject line keyword to search for
    DRIVE_FOLDER_ID   - Google Drive folder ID to upload PDFs to
    GMAIL_LABEL       - Gmail label to apply to processed emails
    TOKEN_FILE        - Path to OAuth token cache (token.pickle)
    CREDENTIALS_FILE  - Path to OAuth credentials JSON

WORKFLOW:
    1. Search Gmail for unread emails matching:
       from:{SENDER_EMAIL} subject:"{SUBJECT_KEYWORD}" is:unread
    2. Extract PDF attachments from matching emails
    3. Upload PDFs to Google Drive folder
    4. Create/apply Gmail label to processed emails
    5. Report summary of processed files

OAUTH SCOPES:
    - gmail.readonly   - Read email messages
    - gmail.modify     - Apply labels to emails
    - drive.file       - Upload files to Drive

EXAMPLES:
    # First run - will open browser for OAuth consent
    python gmail_savepdfs_to_gdrive.py

    # Subsequent runs use cached token
    python gmail_savepdfs_to_gdrive.py

NOTES:
    - Only processes PDF attachments (*.pdf)
    - Creates template .env file if missing
    - OAuth token cached in token.pickle for reuse
    - Emails are marked with label after processing (not deleted)

File: drive_to_gemini_sync.py
==============================

Features:

Polls SOURCE_FOLDER_ID for files
Uploads to Gemini File Search Store (FILE_SEARCH_STORE_ID)
Moves processed files to PROCESSED_FOLDER_ID
Logs to console and logs/sync_YYYYMMDD.log
Supports: PDF, TXT, HTML, CSV, DOCX, PPTX, Google Docs (as PDF), Google Sheets (as CSV)
OAuth2 authentication with token caching
Test Results:

Dry-run executed successfully
OAuth token refreshed automatically
Logs directory created at logs/
No files in source folder currently (ready for use)
Usage:


# Dry run (no changes)
python drive_to_gemini_sync.py --dry-run

# Normal run
python drive_to_gemini_sync.py

# Verbose logging
python drive_to_gemini_sync.py --verbose
Cron Setup (Windows Task Scheduler):

Open Task Scheduler
Create Task with trigger: repeat every 1 hour
Action: python drive_to_gemini_sync.py


file_search_store_cleanup.py
============================

Deletes all documents from a Gemini File Search Store.

USAGE:
    python file_search_store_cleanup.py <store_id> [options]

ARGUMENTS:
    store_id        File Search Store ID (e.g., fileSearchStores/mystore-abc123)
                    Can also use short form: mystore-abc123 (auto-prefixes)

OPTIONS:
    --dry-run       List documents without deleting
    --force         Skip confirmation prompt
    --verbose, -v   Enable debug logging

ENVIRONMENT (.env):
    GEMINI_API_KEY  - Required. API key for Gemini
    TOKEN_FILE      - OAuth token cache path
    CREDENTIALS_FILE - OAuth credentials JSON path

EXAMPLES:
    # List documents (no changes)
    python file_search_store_cleanup.py stanthonyrag-cehk1qjp1dna --dry-run

    # Delete with confirmation prompt
    python file_search_store_cleanup.py stanthonyrag-cehk1qjp1dna

    # Delete without confirmation
    python file_search_store_cleanup.py stanthonyrag-cehk1qjp1dna --force

NOTES:
    - Uses REST API with force=true to delete documents with content/chunks
    - Logs to logs/cleanup_YYYYMMDD.log
    - Requires typing "DELETE ALL" to confirm (unless --force)

chat_server.py
==============

Flask API server that provides a chat interface to query a Gemini File Search Store.
Receives questions via HTTP POST and returns AI-generated answers based on uploaded documents.

USAGE:
    python chat_server.py [--port PORT]

OPTIONS:
    --port PORT     Server port (default: 5000)

ENVIRONMENT (.env):
    GEMINI_API_KEY        - Required. API key for Gemini
    FILE_SEARCH_STORE_ID  - Required. File Search Store to query

ENDPOINTS:
    POST /chat      Send a question, receive an answer
                    Request:  {"question": "What is St Anthony?"}
                    Response: {"answer": "St Anthony is..."}

    GET /health     Health check
                    Response: {"status": "ok", "store_id": "..."}

DEPENDENCIES:
    pip install flask flask-cors google-genai python-dotenv

EXAMPLES:
    # Start server on default port 5000
    python chat_server.py

    # Start on custom port
    python chat_server.py --port 8080

    # Test with curl
    curl -X POST http://localhost:5000/chat \
         -H "Content-Type: application/json" \
         -d '{"question": "Tell me about St Anthony"}'

NOTES:
    - Uses gemini-2.5-flash model with file_search tool
    - CORS enabled for cross-origin requests from web frontend
    - Designed to work with index.html chat page
    - Server binds to 0.0.0.0 (accessible from network)
