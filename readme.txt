FILE: gmail_savepdfs_to_gdrive.py
===================================

This Python script acts as the “Ingestion Layer” for your Development Director AI agent. Its primary job is to automate the bridge between your school staff’s communication (Email) and your digital storage (Google Drive).

Here is a breakdown of the specific logic in the script:

1. The Core Objective

The script monitors a specific Gmail inbox for incoming content from school administrators. It specifically looks for emails that match a predefined “Sender” and “Subject Keyword” (e.g., “School Story”). When it finds a match, it extracts any PDF attachments and uploads them directly to a specific folder in Google Drive.

2. Key Technical Components





OAuth2 / Token Flow: The script uses token.json and credentials.json to handle authentication. It includes a “self-healing” mechanism where, if the access token expires, it uses the Refresh Token to silently log back in without needing a human to click a button.



Environment-Driven Config: It uses python-dotenv to load sensitive information (like your DRIVE_FOLDER_ID and SENDER_EMAIL) from a .env file. This allows you to push the code to GitHub (Epic 5) without leaking your private IDs.



Gmail Filtering: It uses a specific search query: from:{SENDER_EMAIL} subject:"{SUBJECT_KEYWORD}". This prevents the script from accidentally processing unrelated emails or personal correspondence.



Media Handling: It decodes the base64-encoded email attachments and uses MediaInMemoryUpload to stream the PDF directly to Google Drive.

3. Workflow Steps





Authorize: It checks for a valid token.json or refreshes it.



Search: it asks Gmail for a list of messages that look like “School Stories.”



Extract: For every matching email, it scans for files ending in .pdf.



Transfer: It sends those PDFs to the Google Drive folder defined in your .env.



Label (Optional): Many versions of this script also apply a Gmail Label (like “Processed”) to the email so it doesn’t get processed twice.

4. Role in your “Development Director” Roadmap

In the context of your Epic 1 (Content Ingestion), this script is the “hands-free” gatekeeper.





Current State: It moves files to Drive.



Next Step (Epic 3): Once the file is in Drive, your next script (which you’ve also been working on) can grab that PDF and upload it to the Gemini File Search Store to vectorize it for the AI’s “memory.”

Summary: This script turns a simple email from a teacher’s phone into a structured data asset for your fundraising AI, achieving the “unattended” operation required for your MVP.

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
