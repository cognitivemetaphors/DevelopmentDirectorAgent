FILE: gmail_savepdfs_to_gdrive.py

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
