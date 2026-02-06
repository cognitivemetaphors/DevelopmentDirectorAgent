
gmail_saveattachments_to_gdrive.py
==================================

Description:
    Monitors Gmail for unread emails from a specific sender with a specific 
    subject keyword, downloads matching attachments, uploads them to Google 
    Drive, and labels the processed emails.

Usage:
    python gmail_saveattachments_to_gdrive.py

Environment Variables (in .env):
    SENDER_EMAIL      - Email address to filter messages from
    SUBJECT_KEYWORD   - Keyword that must appear in the subject line
    DRIVE_FOLDER_ID   - Google Drive folder ID for uploaded files
    GMAIL_LABEL       - Label to apply to processed emails (default: StAnthonys)
    FILE_EXTENSIONS   - Comma-separated list of file extensions to process
                        (default: pdf). Example: pdf,docx,xlsx,pptx,txt
    TOKEN_FILE        - Path to OAuth token cache (token.pickle)
    CREDENTIALS_FILE  - Path to OAuth credentials JSON

Workflow:
    1. Searches Gmail for unread emails matching sender and subject criteria
    2. For each matching email:
       - Downloads attachments with configured file extensions
       - Uploads files to the specified Google Drive folder
       - Applies a Gmail label to mark the email as processed
    3. Displays summary of processed emails and uploaded files

Features:
    - Configurable file type filtering via FILE_EXTENSIONS in .env
    - OAuth2 authentication with automatic token refresh
    - Creates Gmail labels automatically if they don't exist
    - Supports multiple file types: pdf, docx, xlsx, pptx, txt, csv, html,
      doc, xls, ppt, jpg, jpeg, png, gif
    - Detailed progress output with file sizes and Drive links

Requirements:
    - google-auth
    - google-auth-oauthlib
    - google-api-python-client
    - python-dotenv

OAuth Scopes:
    - gmail.readonly (read emails)
    - gmail.modify (apply labels)
    - drive.file (upload files)

Example .env Configuration:
    SENDER_EMAIL=reports@company.com
    SUBJECT_KEYWORD=Monthly Report
    DRIVE_FOLDER_ID=1ABC123def456
    GMAIL_LABEL=ProcessedReports
    FILE_EXTENSIONS=pdf,docx,xlsx
    TOKEN_FILE=C:\path\to\token.pickle
    CREDENTIALS_FILE=C:\path\to\credentials.json

File: drive_to_gemini_sync.py
==============================

================================================================================
GOOGLE DRIVE TO GEMINI FILE SEARCH STORE SYNC SCRIPT
================================================================================

OVERVIEW
--------
This script automates the process of syncing files from a Google Drive folder
to a Gemini File Search Store. It polls a source folder, uploads supported
file types to the File Search Store, and moves processed files to a designated
folder for organization.

FEATURES
--------
- Automatic polling of Google Drive source folder
- Batch file uploads to Gemini File Search Store
- Support for multiple file formats (PDF, TXT, HTML, CSV, JSON, DOCX, XLSX, PPTX)
- Automatic conversion of Google Docs (to PDF) and Google Sheets (to CSV)
- File tracking and processed file organization
- Comprehensive logging with rotating file handlers
- Dry-run mode for testing without making changes
- OAuth2 authentication for secure access
- Detailed error reporting and retry capability

SUPPORTED FILE TYPES
--------------------
- PDF (.pdf)
- Plain Text (.txt)
- HTML (.html)
- CSV (.csv)
- JSON (.json)
- Microsoft Word (.docx)
- Microsoft Excel (.xlsx)
- Microsoft PowerPoint (.pptx)
- Google Docs (exported as PDF)
- Google Sheets (exported as CSV)

REQUIREMENTS
------------
- Python 3.7 or higher
- Google Drive API enabled in your Google Cloud Project
- Gemini API key
- OAuth 2.0 credentials (OAuth client ID and secret)
- Required Python packages (see Installation)

INSTALLATION
------------
1. Install required Python packages:
   pip install python-dotenv google-auth-oauthlib google-auth google-api-python-client google-genai

2. Set up Google Cloud credentials:
   - Create a Google Cloud Project
   - Enable the Google Drive API
   - Enable the Generative Language API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials JSON file

3. Create a .env file in the script directory with the following variables:
   SOURCE_FOLDER_ID=<your-drive-source-folder-id>
   PROCESSED_FOLDER_ID=<your-drive-processed-folder-id>
   FILE_SEARCH_STORE_ID=<your-gemini-store-id>
   GEMINI_API_KEY=<your-gemini-api-key>
   TOKEN_FILE=./token.pickle
   CREDENTIALS_FILE=./credentials.json

CONFIGURATION
-------------
Environment Variables (in .env):
  SOURCE_FOLDER_ID      - Google Drive folder ID to poll for files
  PROCESSED_FOLDER_ID   - Google Drive folder ID where processed files are moved
  FILE_SEARCH_STORE_ID  - Gemini File Search Store ID (e.g., fileSearchStores/mystore)
  GEMINI_API_KEY        - API key for Gemini API access
  TOKEN_FILE            - Path to OAuth token cache file (created automatically)
  CREDENTIALS_FILE      - Path to your Google OAuth credentials JSON file

How to find folder IDs in Google Drive:
  1. Navigate to the folder in Google Drive
  2. Look at the URL: https://drive.google.com/drive/folders/FOLDER_ID
  3. Copy the FOLDER_ID value

USAGE
-----
Basic syntax:
  python drive_to_gemini_sync.py [--dry-run] [--verbose]

Options:
  --dry-run    Preview files that would be processed without making changes
  --verbose    Enable debug logging for troubleshooting
  -v           Short form of --verbose

Examples:
  # Preview what would be synced
  python drive_to_gemini_sync.py --dry-run

  # Run sync with verbose output
  python drive_to_gemini_sync.py --verbose

  # Standard sync run
  python drive_to_gemini_sync.py

HOW IT WORKS
-----------
1. Configuration Validation
   - Checks that all required environment variables are set
   - Verifies credentials file exists

2. Authentication
   - Authenticates with Google Drive using OAuth2
   - Creates or refreshes access tokens as needed

3. File Processing
   - Lists all files in the source folder
   - Filters files by supported type
   - Downloads files from Google Drive
   - Converts Google Workspace files to compatible formats
   - Uploads files to Gemini File Search Store

4. File Organization
   - Moves successfully processed files to the processed folder
   - Logs any failures for review

5. Summary
   - Reports total files found, processed, skipped, and failed
   - Logs results to rotating file in ./logs/ directory

LOGGING
-------
- Log files are created in the ./logs/ directory
- File naming: sync_YYYYMMDD.log
- Log rotation: Maximum 10MB per file, keeps 7 backup files
- Log level: INFO (console), DEBUG (file)
- Use --verbose flag for DEBUG level console output

TROUBLESHOOTING
---------------
Authentication Issues:
  - Ensure credentials.json is in the correct path
  - Delete token.pickle to force re-authentication
  - Check that Google Drive API is enabled in your project

File Type Errors:
  - Verify files are in a supported format
  - Google Docs/Sheets must be exported through Drive API

Gemini Upload Failures:
  - Verify FILE_SEARCH_STORE_ID is correct
  - Check GEMINI_API_KEY is valid and has proper permissions
  - Ensure store exists and is accessible

Permission Errors:
  - Verify OAuth credentials have Drive access scope
  - Check folder sharing permissions
  - Ensure source and processed folders are accessible

COMMON ISSUES
-------------
Q: Script says "No files to process" but I have files in the folder
A: Files may be in an unsupported format, or they may be folders rather than files

Q: Files are uploaded but not moved to processed folder
A: This is logged as a warning. Check folder permissions and PROCESSED_FOLDER_ID

Q: OAuth prompt doesn't appear
A: Ensure you have a browser available and port 0 is available for local server

Q: Files disappear but don't appear in File Search Store
A: Check GEMINI_API_KEY and FILE_SEARCH_STORE_ID are correct. Review logs for errors.

EXAMPLES
--------
Example 1: Test run (dry-run)
  python drive_to_gemini_sync.py --dry-run
  - Lists all files that would be processed
  - No files are actually uploaded or moved

Example 2: Full sync with logging
  python drive_to_gemini_sync.py --verbose
  - Processes all supported files
  - Uploads to File Search Store
  - Moves files to processed folder
  - Detailed logs to console and file

Example 3: Scheduled sync (cron job on Linux/Mac)
  0 2 * * * cd /path/to/script && python drive_to_gemini_sync.py
  - Runs daily at 2:00 AM
  - Processes new files automatically

SECURITY NOTES
--------------
- Store credentials.json securely and never commit to version control
- Use environment variables for sensitive API keys
- Keep .env file private (add to .gitignore)
- Token.pickle is an OAuth cache file - keep it private
- Review logs regularly for suspicious activity

PERFORMANCE CONSIDERATIONS
---------------------------
- Script processes files sequentially (not in parallel)
- Large files may take time to download and upload
- Check file size limits for Gemini File Search Store
- Consider scheduling during off-peak hours for large batch operations

VERSION HISTORY
---------------
v1.0 (Initial Release)
  - Google Drive to Gemini File Search Store sync
  - Support for PDF, TXT, HTML, CSV, JSON, DOCX, XLSX, PPTX
  - Google Docs/Sheets conversion
  - OAuth2 authentication
  - Dry-run mode
  - Comprehensive logging

SUPPORT
-------
For issues or questions:
  1. Check the troubleshooting section above
  2. Review the log files in ./logs/ directory
  3. Run with --verbose flag for more detailed output
  4. Check Google Cloud Console for API quota and errors
  5. Verify all environment variables are correctly set

file_search_store_cleanup.py
============================

================================================================================
GEMINI FILE SEARCH STORE CLEANUP TOOL
================================================================================

OVERVIEW
--------
This script provides a safe and controlled way to manage documents in a Gemini
File Search Store. It can delete all documents from a store or selectively
delete specific documents by number. The script includes confirmation prompts,
dry-run mode for testing, and comprehensive logging.

FEATURES
--------
- Delete all documents from a File Search Store
- Selectively delete individual documents by number
- Dry-run mode to preview deletions without making changes
- Interactive confirmation prompts with force mode override
- Document listing with display names and IDs
- Detailed logging with file rotation
- OAuth2 authentication for secure access
- Progress tracking during deletion operations
- Comprehensive error reporting
- Summary statistics after each run

REQUIREMENTS
------------
- Python 3.7 or higher
- Google Cloud Project with Generative Language API enabled
- Gemini API key
- OAuth 2.0 credentials for Google authentication
- Required Python packages (see Installation)

INSTALLATION
------------
1. Install required Python packages:
   pip install requests python-dotenv google-auth-oauthlib google-auth google-genai

2. Set up Google Cloud credentials:
   - Create a Google Cloud Project
   - Enable the Generative Language API
   - Enable the Google Cloud Platform API (for OAuth)
   - Create OAuth 2.0 credentials (Desktop application type)
   - Download the credentials JSON file

3. Create a .env file in the script directory with the following variables:
   GEMINI_API_KEY=<your-gemini-api-key>
   TOKEN_FILE=./token.pickle
   CREDENTIALS_FILE=./credentials.json

CONFIGURATION
-------------
Environment Variables (in .env):
  GEMINI_API_KEY        - API key for Gemini API access (required for deletion)
  TOKEN_FILE            - Path to OAuth token cache file (created automatically)
  CREDENTIALS_FILE      - Path to your Google OAuth credentials JSON file

File Search Store ID:
  - Use the format: fileSearchStores/your-store-id
  - Example: fileSearchStores/mystore-abc123
  - You can omit the prefix and the script will add it automatically

USAGE
-----
Basic syntax:
  python file_search_store_cleanup.py <store_id> [OPTIONS]

Arguments:
  store_id              File Search Store ID (required)
                       Format: fileSearchStores/abc123 or just abc123

Options:
  --dry-run            Preview files without deleting
  --force              Skip confirmation prompt
  --files INDICES      Comma-separated document numbers to delete
                      Example: --files 1,3,5
                      If omitted, deletes ALL documents
  --verbose            Enable debug logging
  -v                   Short form of --verbose

USAGE EXAMPLES
--------------

Example 1: List all documents without deleting (dry-run)
  python file_search_store_cleanup.py fileSearchStores/mystore --dry-run

  Output:
  - Shows all documents in the store
  - Displays document names, IDs, and states
  - Reports what would be deleted
  - No actual deletions occur

Example 2: Delete all documents (with confirmation)
  python file_search_store_cleanup.py mystore

  Process:
  1. Lists all documents
  2. Prompts user to type "DELETE ALL" to confirm
  3. Deletes all documents if confirmed
  4. Shows summary of deleted documents

Example 3: Delete specific documents
  python file_search_store_cleanup.py mystore --files 1,3,5

  Process:
  1. Lists all documents (numbered 1-N)
  2. Prompts user to type "DELETE" to confirm
  3. Deletes only documents 1, 3, and 5
  4. Shows summary of results

Example 4: Delete specific files with force flag (no confirmation)
  python file_search_store_cleanup.py mystore --files 2,4 --force

  - Deletes documents 2 and 4 immediately
  - No confirmation prompt
  - Useful for automated scripts

Example 5: Dry-run with verbose logging
  python file_search_store_cleanup.py mystore --dry-run --verbose

  - Shows all documents
  - Displays detailed debug information
  - No deletions occur

HOW IT WORKS
-----------
Step 1: Authentication
  - Authenticates with Google using OAuth2
  - Reuses cached credentials if available
  - Refreshes expired tokens automatically

Step 2: List Documents
  - Retrieves all documents in the File Search Store
  - Displays numbered list with:
    * Document number (1-N)
    * Display name (original file name)
    * Document ID (unique identifier)
    * Document state (ACTIVE, PROCESSING, etc.)

Step 3: Determine Deletion Target
  - If no --files specified: delete all documents
  - If --files specified: validate indices and prepare selected documents
  - Shows what will be deleted in dry-run mode

Step 4: Confirm Deletion
  - Displays warning message
  - Requests typed confirmation:
    * "DELETE ALL" if deleting all documents
    * "DELETE" if deleting specific documents
  - Skipped if --force flag is used

Step 5: Delete Documents
  - Deletes selected documents one by one
  - Uses REST API with force=true flag
  - Reports progress and any errors
  - Logs each deletion for audit trail

Step 6: Summary
  - Reports total documents in store
  - Shows number successfully deleted
  - Shows number of failures (if any)
  - Indicates deletion mode used

DOCUMENT NUMBERING
------------------
When you run the script, documents are displayed as:

#    Display Name                              Document ID                    State
--   Example File 1.pdf                        doc_abc123def456             ACTIVE
--   Another Document.txt                      doc_xyz789uvw012             ACTIVE

To delete documents 1 and 3, use:
  python file_search_store_cleanup.py mystore --files 1,3

The numbering only exists for this session. Document IDs are permanent.

LOGGING
-------
- Log files are created in the ./logs/ directory
- File naming: cleanup_YYYYMMDD.log
- Log rotation: Maximum 10MB per file, keeps 7 backup files
- Log level: INFO (console), DEBUG (file)
- Use --verbose flag for DEBUG level console output
- Logs track authentication, document listing, and each deletion

CONFIRMATION PROMPTS
--------------------
Delete All Mode (default):
  WARNING: This will DELETE ALL DOCUMENTS from:
    Store: fileSearchStores/mystore
    Total documents: 25
  Type "DELETE ALL" to confirm (or anything else to cancel):

Delete Specific Mode (with --files):
  WARNING: This will DELETE the selected documents from:
    Store: fileSearchStores/mystore
    Documents to delete: 3
  Type "DELETE" to confirm (or anything else to cancel):

FORCE MODE
----------
Use --force to skip the confirmation prompt:
  python file_search_store_cleanup.py mystore --force
  python file_search_store_cleanup.py mystore --files 1,2,3 --force

WARNING: This cannot be undone. Use with caution in automated scripts.

TROUBLESHOOTING
---------------
Authentication Issues:
  Problem: OAuth prompt doesn't appear
  Solution: Ensure you have a web browser available
           Check that port 0 is available for the local server
           Delete token.pickle to force re-authentication

  Problem: "Credentials file not found"
  Solution: Verify CREDENTIALS_FILE path in .env is correct
           Ensure credentials.json file exists
           Check file permissions

Invalid File Indices:
  Problem: "Document number X is out of range"
  Solution: Check the listed documents
           Use numbers from the displayed list (1-N)
           Avoid using document IDs instead of numbers

  Problem: "Invalid file indices. Use comma-separated numbers"
  Solution: Use format: --files 1,3,5
           Don't include spaces unless they're part of numbers
           Only use numeric values

API Errors:
  Problem: "Failed to list documents"
  Solution: Verify GEMINI_API_KEY is valid
           Check File Search Store ID is correct
           Ensure store exists and you have access

  Problem: "Failed" shown for specific documents
  Solution: Document may have special state
           Check logs for detailed error message
           Try using --force flag option

Store ID Issues:
  Problem: Script says store not found
  Solution: Verify store ID format: fileSearchStores/xyz
           You can use just "xyz" and script will format it
           Check that store exists in your project

COMMON QUESTIONS
----------------
Q: Can I recover deleted documents?
A: No. This operation is permanent. Always use --dry-run first.

Q: How do I delete just one document?
A: Use --files with the document number, e.g., --files 5

Q: Can I delete documents 1-10 quickly?
A: Yes, use --files 1,2,3,4,5,6,7,8,9,10 or create the list programmatically

Q: What happens if deletion fails for some documents?
A: The script continues with other documents and reports failures in summary

Q: Is --force flag safe to use?
A: Use --force only in trusted automated environments
  Always test with --dry-run first

Q: How do I find my File Search Store ID?
A: Check your Gemini project settings or API documentation
  Format is usually: fileSearchStores/YOUR-STORE-ID

Q: Can I schedule this to run automatically?
A: Yes, use cron jobs or task scheduler with --force flag
  Always include --dry-run test first

Q: What's the difference between deleting and archiving?
A: This tool only deletes. There is no archive feature.

SECURITY NOTES
--------------
- Store credentials.json securely and never commit to version control
- Keep GEMINI_API_KEY private in .env file
- Add .env to .gitignore to prevent accidental commits
- Token.pickle is an OAuth cache file - keep it private
- Use --dry-run before any automated deletions
- Review logs regularly for unexpected activity
- Don't share store IDs if access should be restricted

PERFORMANCE NOTES
-----------------
- Deletion speed depends on number of documents
- Each document deletion requires one API call
- Large stores may take several minutes to clear completely
- Progress is shown in real-time during deletion
- Deletion is sequential (not parallelized)

ADVANCED USAGE
--------------
Cron Job Example (delete store nightly):
  0 2 * * * cd /path/to/script && python file_search_store_cleanup.py mystore --force

Dry-run in cron (test before scheduling real deletion):
  0 2 * * * cd /path/to/script && python file_search_store_cleanup.py mystore --dry-run

Delete specific documents monthly:
  0 3 1 * * cd /path/to/script && python file_search_store_cleanup.py mystore --files 1,2,3 --force

VERSION HISTORY
---------------
v2.0 (Current)
  - Added selective document deletion with --files option
  - Separate confirmation prompts for all vs. selective deletion
  - Improved error handling and validation
  - Enhanced summary reporting

v1.0 (Previous)
  - Delete all documents from File Search Store
  - OAuth2 authentication
  - Dry-run mode
  - Comprehensive logging

SUPPORT & FEEDBACK
------------------
For issues:
  1. Check the troubleshooting section above
  2. Review logs in ./logs/ directory
  3. Run with --verbose for more details
  4. Verify all environment variables in .env
  5. Test with --dry-run before actual deletion

Tips for success:
  - Always run --dry-run first to see what will be deleted
  - Keep CREDENTIALS_FILE and GEMINI_API_KEY secure
  - Review logs after each run
  - Test automated schedules with --dry-run

================================================================================

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
