```mermaid
flowchart LR 
        A(["Start"])
        A --emails about school--> B["Gmail_saveattachments_to_gdrive"]
        B --content creation prompt/skill + add article to vector memory-->D["drive_to_gemini_sync"]
        D -- vector memory-->E["chat_server"]
        E --vector memory, feature story images & jsons -->H["index.html"]
        H --booking requests-->E
        E -->|booking email| G["Gmail"]
        G -->|booking approaval| K["Google Calendar"]
        A --> J
        J["substack blog"]--substack entries-->L["substack_to_filesearchstore"]
        L --vector memory-->E
        H --> I(["End"])
```
gmail_saveattachments_to_gdrive.py
====================================

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

================================================================================
                          CHAT SERVER - README
================================================================================

PROJECT: Joy & Caregiving Foundation
PURPOSE: Flask-based API server for chat and feature story management
VERSION: 2.0

================================================================================
OVERVIEW
================================================================================

chat_server.py is a Flask REST API that provides two main functions:

1. CHAT ENDPOINT - Query Gemini AI using File Search Store
   - Accepts natural language questions
   - Searches uploaded documents for answers
   - Returns AI-generated responses

2. FEATURE STORY ENDPOINT - Load and serve feature content
   - Reads JSON files from local data directory
   - Returns formatted feature story data
   - Supports dynamic feature selection via indexname

The server automatically reloads environment variables before each request,
allowing configuration changes without server restart.

================================================================================
INSTALLATION & SETUP
================================================================================

1. INSTALL DEPENDENCIES:
   pip install flask flask-cors python-dotenv google-genai

2. CREATE .ENV FILE (in developmentdirectoragent/ directory):
   GEMINI_API_KEY=your_api_key_here
   FILE_SEARCH_STORE_ID=your_store_id_here
   FEATURED_STORY_INDEXNAME=feature001

3. CREATE DATA DIRECTORY:
   mkdir -p /var/www/joyandcaregiving/data

4. ADD JSON FEATURE FILES:
   Place JSON files in the data directory:
   - Option A: Individual files (feature001.json, feature002.json, etc.)
   - Option B: Single features.json with array of features

   JSON Format:
   {
     "indexname": "feature001",
     "title": "Feature Title",
     "description": "Feature description text",
     "hashtags": ["tag1", "tag2"] OR "tag1, tag2",
     "image_link": "filename.jpg" or null,
     "youtube_link": "https://youtube.com/watch?v=..." or null
   }

================================================================================
RUNNING THE SERVER
================================================================================

COMMAND LINE:
   python chat_server.py --port 5000

DEFAULT PORT: 5000

SYSTEMD SERVICE (if installed):
   sudo systemctl start chat-server
   sudo systemctl restart chat-server
   sudo systemctl status chat-server

VIEW LOGS:
   journalctl -u chat-server -f

================================================================================
API ENDPOINTS
================================================================================

1. POST /chat
   Purpose: Ask questions, get AI responses from documents

   Request:
   {
     "question": "What is the mission of Joy & Caregiving Foundation?"
   }

   Response:
   {
     "answer": "The foundation's mission is to..."
   }

2. GET /feature-story
   Purpose: Get feature story data by indexname

   Parameters:
   - indexname (optional): Which feature to load
                          Uses FEATURED_STORY_INDEXNAME from .env if not provided

   Example: GET /feature-story?indexname=feature001

   Response:
   {
     "indexname": "feature001",
     "title": "Feature Title",
     "description": "Description text",
     "hashtags": ["tag1", "tag2"],
     "image_link": "filename.jpg",
     "youtube_link": "https://youtube.com/watch?v=..."
   }

   Errors:
   - 400: No indexname specified and FEATURED_STORY_INDEXNAME not in .env
   - 404: Specified feature not found in data directory

3. GET /config
   Purpose: Get frontend configuration

   Response:
   {
     "featured_story_indexname": "feature001"
   }

4. GET /health
   Purpose: Health check endpoint

   Response:
   {
     "status": "ok",
     "store_id": "your_store_id"
   }

5. GET /test-gemini
   Purpose: Test Gemini API connectivity

   Response:
   {
     "status": "success",
     "message": "Gemini API is working",
     "response": "Hello, testing Gemini API"
   }

================================================================================
ENVIRONMENT VARIABLES
================================================================================

GEMINI_API_KEY (required)
   - Your Gemini API key from Google Cloud
   - Used to authenticate with Gemini AI

FILE_SEARCH_STORE_ID (required)
   - ID of your File Search Store in Gemini
   - Contains documents used by /chat endpoint

FEATURED_STORY_INDEXNAME (optional)
   - Default feature to load on /feature-story if no indexname parameter
   - Example: "feature001"
   - Can be changed in .env file without restarting server

NOTE: Environment variables are automatically reloaded before each request,
so changes to .env take effect immediately without server restart.

================================================================================
FILE STRUCTURE
================================================================================

/var/www/joyandcaregiving/
├── chat_server.py              ← Main server file
├── public/
│   ├── index.html              ← Frontend HTML
│   ├── images/                 ← Feature story images
│   │   ├── children_jollibee.jpg
│   │   └── [other images]
│   └── [other static files]
├── data/                        ← Feature story JSON files
│   ├── feature001.json
│   ├── feature002.json
│   └── features.json (optional)
├── developmentdirectoragent/
│   └── .env                    ← Configuration file
└── logs/                        ← Log files (if configured)

================================================================================
FEATURE STORY DATA LOADING
================================================================================

The /feature-story endpoint loads JSON data in this order:

1. Checks for individual feature file:
   /var/www/joyandcaregiving/data/{indexname}.json

2. If not found, checks features.json for array or nested structure:
   /var/www/joyandcaregiving/data/features.json

3. Handles nested social_media_post structure:
   If data has "social_media_post" object, extracts values to root level

4. Returns clean, flat JSON with all fields available

================================================================================
LOGGING
================================================================================

LOG LEVEL: INFO

Logs are sent to console and can be viewed via:
- Local: stdout/stderr
- Systemd: journalctl -u chat-server

Log entries include:
- Configuration reloads
- Feature story loads
- API errors
- Gemini API responses and errors

================================================================================
TROUBLESHOOTING
================================================================================

ISSUE: Feature story shows blank/no content
SOLUTION:
- Check browser console (F12) for JavaScript errors
- Verify /feature-story endpoint returns data
- Check that .env file has FEATURED_STORY_INDEXNAME set
- Verify data directory and JSON files exist

ISSUE: "Missing GEMINI_API_KEY" on startup
SOLUTION:
- Check .env file exists in developmentdirectoragent/ directory
- Verify GEMINI_API_KEY and FILE_SEARCH_STORE_ID are set
- Server will not start without these values

ISSUE: /chat endpoint returns empty response
SOLUTION:
- Verify File Search Store ID is correct
- Check that documents were uploaded to File Search Store
- Try /test-gemini endpoint to verify Gemini API is working

ISSUE: Feature not found (404 error)
SOLUTION:
- Verify JSON file exists in /var/www/joyandcaregiving/data/
- Check that indexname matches the JSON filename or "indexname" field
- Verify JSON format is valid

ISSUE: Images not showing in feature story
SOLUTION:
- Verify image files exist in /var/www/joyandcaregiving/public/images/
- Check that image_link in JSON matches actual filename

================================================================================
DEPLOYMENT & MAINTENANCE
================================================================================

CONFIGURATION CHANGES:
   - Edit .env file with new values
   - Changes take effect automatically on next request
   - No server restart required

FEATURE UPDATES:
   - Update JSON files in /data directory
   - Changes available immediately on next API call

CODE UPDATES:
   - Update chat_server.py file
   - Restart server: sudo systemctl restart chat-server

================================================================================
VERSION HISTORY
================================================================================

v2.0 - Current
- Replaced Gemini-based feature story with local JSON file reading
- Added automatic .env reloading before each request
- Support for nested social_media_post structure
- Improved hashtags handling (string and array support)

v1.0 - Initial release
- Chat endpoint with Gemini File Search
- Feature story endpoint with Gemini extraction

================================================================================

index.html
==========

================================================================================
                    INDEX.HTML - FRONTEND DOCUMENTATION
================================================================================

PROJECT: Joy & Caregiving Foundation Website
PURPOSE: Landing page with dynamic feature story display
VERSION: 2.0

================================================================================
OVERVIEW
================================================================================

index.html is the main landing page for the Joy & Caregiving Foundation website.
It provides:

1. RESPONSIVE DESIGN
   - Mobile-friendly layout
   - Works on all screen sizes (desktop, tablet, mobile)
   - Sticky navigation header

2. FEATURE STORY SECTION
   - Displays dynamic content from the backend API
   - Shows title, description, hashtags
   - Supports image and YouTube video display
   - Automatically loads from /feature-story endpoint

3. NAVIGATION & SECTIONS
   - Multiple page sections (Home, About, Programs, Donate, Contact)
   - Smooth scrolling between sections
   - Mobile menu with hamburger icon

4. CALL-TO-ACTION
   - Donation button
   - Contact information
   - Email subscription option

================================================================================
FILE LOCATION
================================================================================

/var/www/joyandcaregiving/public/index.html

This file must be served by a web server (nginx, Apache, etc.) or accessed
via http://143.42.1.253/ in a browser.

================================================================================
DEPENDENCIES
================================================================================

BACKEND API:
- /config endpoint
  Returns: {"featured_story_indexname": "feature001"}

- /feature-story endpoint
  Returns: {
    "indexname": "...",
    "title": "...",
    "description": "...",
    "hashtags": [...],
    "image_link": "...",
    "youtube_link": "..."
  }

EXTERNAL LIBRARIES:
- None (uses vanilla JavaScript, CSS, and HTML)
- No jQuery, Bootstrap, or other frameworks required

================================================================================
PAGE STRUCTURE
================================================================================

HEADER / NAVIGATION
- Logo and site title
- Navigation links (Home, About, Programs, Donate, Contact)
- Mobile menu button (hamburger icon)
- Sticky positioning (stays at top when scrolling)

HERO SECTION
- Large banner with organization mission statement
- Call-to-action buttons
- Background styling

ABOUT SECTION
- Description of organization
- Mission statement
- Statistics or key information

FEATURE STORY SECTION (Dynamic)
- Title: From API
- Description: From API
- Image: From /public/images/ directory (if available)
- Hashtags: From API (displayed as tags)
- YouTube Video: From API (embedded iframe)
- Loading indicator while fetching data
- Error message if API fails

PROGRAMS SECTION
- Description of programs offered
- Program cards/details

DONATE SECTION
- Donation information
- Donation button/link
- Payment methods accepted

CONTACT SECTION
- Contact form
- Email address: jcgfoundation@yahoo.com
- Location information
- Social media links

FOOTER
- Copyright information
- Links
- Contact information

================================================================================
FEATURE STORY FUNCTIONALITY
================================================================================

HOW IT WORKS:

1. PAGE LOADS
   - index.html loads in browser
   - JavaScript initializes

2. FETCH CONFIGURATION
   - JavaScript calls /config endpoint
   - Retrieves FEATURED_STORY_INDEXNAME from backend
   - Example: Returns "feature001"

3. LOAD FEATURE STORY
   - JavaScript calls /feature-story?indexname=feature001
   - Shows loading indicator while fetching

4. PROCESS RESPONSE
   - Parse JSON response from API
   - Extract: title, description, hashtags, image_link, youtube_link

5. DISPLAY CONTENT
   - Set title in HTML
   - Display description as text
   - If image_link exists: display image from /public/images/
   - If hashtags exist: display as styled tags
   - If youtube_link exists: extract video ID and embed YouTube player

6. ERROR HANDLING
   - If API fails: show error message
   - If image fails to load: hide image container
   - If YouTube video unavailable: hide video container

================================================================================
HASHTAGS PROCESSING
================================================================================

The JavaScript handles hashtags in two formats:

STRING FORMAT (comma-separated):
Input: "tag1, tag2, tag3"
Processing: Split by comma, trim whitespace, remove # prefix
Output: Displayed as individual styled tags

ARRAY FORMAT:
Input: ["tag1", "tag2", "tag3"]
Processing: Map over array, remove # prefix
Output: Displayed as individual styled tags

DISPLAY:
Each hashtag appears as a purple rounded tag with # prefix:
  #EducationForAll  #StAnthonyDLC  #CommunityDevelopment

================================================================================
IMAGE HANDLING
================================================================================

IMAGE SOURCE:
- Images stored in: /var/www/joyandcaregiving/public/images/
- Filename referenced in JSON: "children_jollibee.jpg"
- Full path: /public/images/children_jollibee.jpg

SUPPORTED FORMATS:
- .jpg, .jpeg
- .png
- .gif
- .webp

IMAGE CONFIGURATION:
- Responsive sizing: scales with container
- Border radius: rounded corners
- Error handling: if image fails to load, container is hidden

FALLBACK BEHAVIOR:
- If image_link is null or missing: image container is hidden
- If image fails to load: error listener hides container
- Page continues to display other content

================================================================================
YOUTUBE VIDEO HANDLING
================================================================================

SUPPORTED URL FORMATS:
1. Standard: https://www.youtube.com/watch?v=VIDEO_ID
2. Short: https://youtu.be/VIDEO_ID
3. Embed: https://www.youtube.com/embed/VIDEO_ID

VIDEO ID EXTRACTION:
JavaScript extracts the video ID from any format and constructs embed URL:
  https://www.youtube.com/embed/{VIDEO_ID}

EMBEDDING:
- Uses iframe for secure embedding
- Aspect ratio: 16:9 (widescreen)
- Responsive: scales with container
- Features: play controls, fullscreen option

FALLBACK BEHAVIOR:
- If youtube_link is null or missing: video container is hidden
- If video ID cannot be extracted: video container is hidden
- Page continues to display other content

================================================================================
STYLING & DESIGN
================================================================================

COLOR SCHEME:
- Primary Purple: #7c3aed
- Secondary Purple: #6b21a8
- Text: #333
- Light backgrounds: #f7fafc
- Tag background: #e9d5ff

FONTS:
- System fonts (Apple, Windows, Linux defaults)
- Fallback chain: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto

RESPONSIVE BREAKPOINTS:
- Desktop: 1200px max-width container
- Tablet: Responsive padding and layouts
- Mobile: Single column, full-width elements

STYLING FEATURES:
- Shadows for depth
- Gradients for visual interest
- Border radius for modern look
- Smooth transitions and hover effects
- Box-shadow on cards and containers

================================================================================
CUSTOMIZATION
================================================================================

CHANGE FEATURE STORY:
1. Edit .env file: FEATURED_STORY_INDEXNAME=feature002
2. Restart server: sudo systemctl restart chat-server
3. Reload page: F5 or Ctrl+R

CHANGE COLORS:
1. Edit index.html CSS section (look for hex color codes)
2. Find color like #7c3aed (purple)
3. Replace with desired color
4. Save and reload page

CHANGE SITE TITLE:
1. Find <title> tag at top of HTML
2. Change text between <title> tags
3. Change <h1 id="site-title"> text in header

CHANGE LOGO:
1. Replace logo image in /var/www/joyandcaregiving/public/
2. Update <img src="logo.png"> path in HTML
3. Adjust width/height in CSS if needed

ADD NEW SECTIONS:
1. Create new <section> element with unique ID
2. Add navigation link in header
3. Add CSS styling in <style> section
4. Update scroll-to-section JavaScript if needed

================================================================================
JAVASCRIPT FUNCTIONS
================================================================================

fetchConfig()
- Purpose: Load configuration from /config endpoint
- Updates: FEATURED_STORY_INDEXNAME global variable
- Called: On page load

loadFeatureStory()
- Purpose: Fetch feature story data from /feature-story endpoint
- Shows: Loading indicator
- Calls: displayFeatureStory() on success
- Handles: Errors and displays error message

displayFeatureStory(story)
- Purpose: Render feature story data to HTML
- Updates: Title, description, hashtags, image, video
- Handles: Different data formats (string/array hashtags)
- Error handling: Missing fields and failed image loads

extractYouTubeId(url)
- Purpose: Extract video ID from YouTube URL
- Supports: Multiple YouTube URL formats
- Returns: Video ID or null

showElement(id, visible)
- Purpose: Toggle element visibility
- Parameters: Element ID and visibility boolean

hideElement(id)
- Purpose: Hide element
- Parameters: Element ID

showError(message)
- Purpose: Display error message
- Parameters: Error text to display

================================================================================
ERROR MESSAGES
================================================================================

LOADING FEATURE STORY...
- Normal state during initial API call
- Shows while waiting for data

Unable to load feature story: {error message}
- API endpoint returned error
- Feature not found (404)
- API is down
- Network error

Check browser console (F12) for detailed error information

================================================================================
BROWSER COMPATIBILITY
================================================================================

TESTED ON:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

REQUIRES:
- JavaScript enabled
- Fetch API support
- ES6+ JavaScript features

MOBILE:
- iOS Safari 12+
- Android Chrome
- Mobile Firefox

================================================================================
LOADING STATE
================================================================================

BEFORE API RESPONSE:
- Show: storyLoadingContainer (spinning loader)
- Hide: featureStoryContainer, storyErrorContainer

ON SUCCESS:
- Hide: storyLoadingContainer
- Show: featureStoryContainer with data

ON ERROR:
- Hide: storyLoadingContainer
- Show: storyErrorContainer with error message

================================================================================
PERFORMANCE CONSIDERATIONS
================================================================================

PAGE LOAD TIME:
- HTML parsing: ~10-50ms
- CSS rendering: ~20-100ms
- JavaScript execution: ~10-50ms
- API fetch: 100-500ms (network dependent)
- Total: ~150-700ms (varies by network)

OPTIMIZATION TIPS:
1. Cache API responses in browser
2. Lazy load images
3. Minify CSS/JavaScript for production
4. Use CDN for static files
5. Enable gzip compression on server

NETWORK REQUESTS:
- 1 request to /config
- 1 request to /feature-story
- Multiple requests for images (if displayed)
- 1 request for each YouTube video (embedded from youtube.com)

================================================================================
DEBUGGING
================================================================================

OPEN DEVELOPER TOOLS: F12 or right-click → Inspect

CONSOLE TAB:
- Look for JavaScript errors (red text)
- Look for warnings (yellow text)
- Check for network request errors

NETWORK TAB:
- Click /config request to see response
- Click /feature-story request to see response
- Check status codes (200 = success, 404 = not found, 500 = error)

ELEMENTS TAB:
- Inspect HTML structure
- Check if elements are hidden (display: none)
- Verify CSS styles are applied

COMMON ISSUES:

Nothing displaying:
- Check browser console for errors
- Verify API endpoints are running
- Check /config response in Network tab

Feature story blank:
- Check /feature-story response in Network tab
- Verify JSON has required fields
- Check that API is returning data (not null)

Image not showing:
- Verify file exists in /public/images/
- Check image_link matches filename
- Look for 404 errors in Network tab

Video not playing:
- Verify youtube_link is valid URL
- Check that URL contains video ID
- Try URL in new tab to verify it works

================================================================================
CUSTOMIZATION EXAMPLES
================================================================================

CHANGE FEATURED STORY:

Option 1: Via Environment Variable
  Edit .env file:
  FEATURED_STORY_INDEXNAME=feature002

Option 2: Via URL Parameter
  Load different feature in browser:
  http://143.42.1.253/?indexname=feature002
  (Note: this requires JavaScript to handle query params - not currently implemented)

ADD CUSTOM CSS:

In <style> section, add:
  .custom-class {
    color: red;
    font-size: 20px;
  }

Then use in HTML:
  <p class="custom-class">Custom text</p>

CHANGE API ENDPOINTS:

Find these lines:
  const FEATURE_STORY_API = 'http://143.42.1.253:5000/feature-story';
  const CONFIG_API = 'http://143.42.1.253:5000/config';

Update URLs if API server moves to different host/port

================================================================================
PRODUCTION DEPLOYMENT
================================================================================

WEB SERVER CONFIGURATION:

NGINX:
  server {
      listen 80;
      server_name yourdomain.com;

      location / {
          root /var/www/joyandcaregiving/public;
          index index.html;
      }

      location /api/ {
          proxy_pass http://localhost:5000/;
      }
  }

APACHE:
  <VirtualHost *:80>
      ServerName yourdomain.com
      DocumentRoot /var/www/joyandcaregiving/public
      <Directory /var/www/joyandcaregiving/public>
          AllowOverride All
      </Directory>
  </VirtualHost>

CACHING:
  Add headers to serve static content with cache:
  
  # Cache static files for 1 year
  <FilesMatch "\.(jpg|jpeg|png|gif|ico|css|js)$">
    Header set Cache-Control "max-age=31536000, public"
  </FilesMatch>

HTTPS:
  Always use HTTPS in production
  Obtain SSL certificate (Let's Encrypt is free)
  Redirect HTTP to HTTPS

================================================================================
VERSION HISTORY
================================================================================

v2.0 - Current
- Support for nested social_media_post JSON structure
- Improved hashtags handling (both string and array formats)
- Better error messages and loading states
- Fixed image and video display logic
- Mobile-optimized navigation

v1.0 - Initial release
- Basic landing page structure
- Feature story section
- Navigation and sections
- Responsive design

================================================================================
SUPPORT & CONTACT
================================================================================

FOR QUESTIONS:
- Email: jcgfoundation@yahoo.com
- Check browser console for detailed error messages
- Review README files for API and server documentation

FILES RELATED TO THIS PAGE:
- chat_server.py: Backend API server
- README.txt: Chat server documentation
- /public/images/: Feature story images
- developmentdirectoragent/.env: Configuration file

================================================================================

substack_to_filesearchstore.py
===============================
Syncs all published posts from a Substack blog into a Google Gemini File Search Store. Designed to be run repeatedly — it detects previously uploaded posts and only uploads new ones.

## How it works

1. Fetches all posts from the Substack API (`/api/v1/posts`)
2. Checks which posts are already in the File Search Store (matched by display name)
3. Converts new posts from HTML to plain text
4. Uploads each new post as a separate `.txt` document
5. On the first run, creates a new File Search Store and saves the ID to `.env`

## Setup

### Dependencies

```
pip install requests beautifulsoup4 python-dotenv google-genai
```

### Environment variables (in `.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google AI Studio API key | `AIzaSy...` |
| `SUBSTACK_URL` | Base URL of the Substack blog | `https://acgarcia21.substack.com` |
| `SUBSTACK_STORE_ID` | File Search Store ID (auto-created on first run) | `fileSearchStores/substackblog-abc123` |

## Usage

```
python substack_to_filesearchstore.py
```

### First run

Creates a new File Search Store, uploads all posts, and saves `SUBSTACK_STORE_ID` to `.env`:

```
Creating new File Search Store "SubstackBlog"...
Created store: fileSearchStores/substackblog-5jlx2i33k1ir
Saved SUBSTACK_STORE_ID to .env
Fetching posts from https://acgarcia21.substack.com...
Found 38 post(s)
  UPLOAD: Ship code, Deploy (4765 chars)
  UPLOAD: Tighten Up Your Brand (4849 chars)
  ...
```

### Subsequent runs

Skips already-uploaded posts, only uploads new ones:

```
Using existing store: fileSearchStores/substackblog-5jlx2i33k1ir
  39 document(s) already in store
Found 40 post(s)
  SKIP (already uploaded): Ship code, Deploy
  SKIP (already uploaded): Tighten Up Your Brand
  UPLOAD: My Newest Post (3200 chars)
```

## Querying the store

Once posts are uploaded, you can query them via the `/substack` endpoint on `chat_server.py`:

```
POST /substack
Content-Type: application/json

{"question": "What did Anthony write about agile?"}
```
# substack_to_filesearchstore.py

Syncs all published posts from a Substack blog into a Google Gemini File Search Store. Designed to be run repeatedly — it detects previously uploaded posts and only uploads new ones.

## How it works

1. Fetches all posts from the Substack API (`/api/v1/posts`)
2. Checks which posts are already in the File Search Store (matched by display name)
3. Converts new posts from HTML to plain text
4. Uploads each new post as a separate `.txt` document
5. On the first run, creates a new File Search Store and saves the ID to `.env`

## Setup

### Dependencies

```
pip install requests beautifulsoup4 python-dotenv google-genai
```

### Environment variables (in `.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google AI Studio API key | `AIzaSy...` |
| `SUBSTACK_URL` | Base URL of the Substack blog | `https://acgarcia21.substack.com` |
| `SUBSTACK_STORE_ID` | File Search Store ID (auto-created on first run) | `fileSearchStores/substackblog-abc123` |

## Usage

```
python substack_to_filesearchstore.py
```

### First run

Creates a new File Search Store, uploads all posts, and saves `SUBSTACK_STORE_ID` to `.env`:

```
Creating new File Search Store "SubstackBlog"...
Created store: fileSearchStores/substackblog-5jlx2i33k1ir
Saved SUBSTACK_STORE_ID to .env
Fetching posts from https://acgarcia21.substack.com...
Found 38 post(s)
  UPLOAD: Ship code, Deploy (4765 chars)
  UPLOAD: Tighten Up Your Brand (4849 chars)
  ...
```

### Subsequent runs

Skips already-uploaded posts, only uploads new ones:

```
Using existing store: fileSearchStores/substackblog-5jlx2i33k1ir
  39 document(s) already in store
Found 40 post(s)
  SKIP (already uploaded): Ship code, Deploy
  SKIP (already uploaded): Tighten Up Your Brand
  UPLOAD: My Newest Post (3200 chars)
```

## Querying the store

Once posts are uploaded, you can query them via the `/substack` endpoint on `chat_server.py`:

```
POST /substack
Content-Type: application/json

{"question": "What did Anthony write about agile?"}
```

# booking_manager.py

Handles meeting booking with a human-in-the-loop approval flow. Used as a library by `chat_server.py` — not run as a standalone service.

## How it works

1. A visitor requests a meeting through the `/substack` chat interface
2. Gemini extracts meeting details (name, email, date, time, duration, purpose) via function calling
3. `booking_manager` checks Google Calendar availability using the FreeBusy API
4. If the slot is free, it stores a pending booking in SQLite and emails Anthony an approval request with Approve/Decline buttons
5. Anthony clicks Approve or Decline from the email
6. On approval: a Google Calendar event is created (with the requester as an attendee) and a confirmation email is sent to the requester

## Dependencies

Requires the same packages as `chat_server.py`, plus:

```
pip install google-api-python-client google-auth google-auth-oauthlib
```

## Google APIs required

Enable these in the [Google Cloud Console](https://console.cloud.google.com/apis/library) for your project:

- **Google Calendar API** — availability checks and event creation
- **Gmail API** — sending approval and confirmation emails

## OAuth token

`booking_manager.py` uses `token.json` (generated by `get_token.py`) for OAuth credentials. The token must include the `gmail.send` and `calendar` scopes. To regenerate:

```
del token.json
python get_token.py
```

Then deploy `token.json` to the server.

## Environment variables (in `.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `TOKEN_FILE` | Path to OAuth token file | `/var/www/cognitivemetaphors/token.json` |
| `CREDENTIALS_FILE` | Path to OAuth client secrets | `/var/www/cognitivemetaphors/credentials.json` |
| `DB_PATH` | Path to SQLite database (auto-created) | `/var/www/cognitivemetaphors/bookings.db` |
| `SERVER_BASE_URL` | Base URL for approval/decline links in emails | `http://143.42.1.253:5000` |

## Database

SQLite database (`bookings.db`) is created automatically on the first booking request. Schema:

| Column | Type | Description |
|--------|------|-------------|
| `approval_token` | TEXT | Unique token used in approve/decline URLs |
| `status` | TEXT | `pending`, `approved`, or `declined` |
| `requester_name` | TEXT | Name of the person requesting the meeting |
| `requester_email` | TEXT | Email for confirmation and calendar invite |
| `meeting_date` | TEXT | Date in `YYYY-MM-DD` format |
| `meeting_time` | TEXT | Time in `HH:MM` 24-hour format (Eastern) |
| `duration_minutes` | INTEGER | Meeting length in minutes |
| `purpose` | TEXT | Topic or reason for the meeting |

## Endpoints (served by chat_server.py)

| Endpoint | Description |
|----------|-------------|
| `GET /approve-booking/<token>` | Anthony clicks this from the approval email |
| `GET /decline-booking/<token>` | Anthony clicks this to decline |
| `GET /booking-status/<token>` | Check booking status (pending/approved/declined) |

