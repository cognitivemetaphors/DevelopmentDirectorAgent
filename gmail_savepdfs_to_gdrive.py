import os
import base64
import pickle
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

# Load environment variables from .env file
# Specify the path to your .env file here
ENV_FILE_PATH = r'.env'

if not os.path.exists(ENV_FILE_PATH):
    print(f'✗ Error: .env file not found at: {ENV_FILE_PATH}')
    print('\nCreating template .env file...')
    with open(ENV_FILE_PATH, 'w') as f:
        f.write('SENDER_EMAIL=your_sender@example.com\n')
        f.write('SUBJECT_KEYWORD=Your Subject Keyword\n')
        f.write('DRIVE_FOLDER_ID=your_folder_id\n')
        f.write('GMAIL_LABEL=Your Gmail Label\n')
        f.write('TOKEN_FILE=Your token file\n')
        f.write('CREDENTIALS_FILE=Your credentials file\n')
    print(f'✓ Template .env file created at: {ENV_FILE_PATH}')
    print('Please edit it with your actual values and run again.')
    exit(1)

load_dotenv(ENV_FILE_PATH)

# Configuration from environment variables
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SUBJECT_KEYWORD = os.getenv('SUBJECT_KEYWORD')
DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')
GMAIL_LABEL = os.getenv('GMAIL_LABEL', 'StAnthonys')

# OAuth2 settings from environment variables
TOKEN_FILE = os.getenv('TOKEN_FILE', r'Unknown')
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE', r'Unknown')

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',  # Need modify to apply labels
    'https://www.googleapis.com/auth/drive.file'
]


def validate_env_variables():
    """Validate that all required environment variables are set."""
    required_vars = {
        'SENDER_EMAIL': SENDER_EMAIL,
        'SUBJECT_KEYWORD': SUBJECT_KEYWORD,
        'DRIVE_FOLDER_ID': DRIVE_FOLDER_ID,
        'GMAIL_LABEL': GMAIL_LABEL,
        'TOKEN_FILE': TOKEN_FILE,
        'CREDENTIALS_FILE': CREDENTIALS_FILE
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        print('✗ Error: Missing required environment variables in .env file:')
        for var in missing_vars:
            print(f'  - {var}')
        print('\nPlease update your .env file with the following variables:')
        print('SENDER_EMAIL=your_sender@example.com')
        print('SUBJECT_KEYWORD=Your Subject Keyword')
        print('DRIVE_FOLDER_ID=your_folder_id')
        print('GMAIL_LABEL=Your Gmail Label')
        print('TOKEN_FILE=Path to your token file')
        print('CREDENTIALS_FILE=Path to your credentials file')
        return False
    
    return True


def get_credentials():
    """Get valid user credentials from storage or run OAuth flow."""
    creds = None
    
    # Check if we have saved credentials
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials are invalid or don't exist, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print('  Refreshing access token...')
            creds.refresh(Request())
        else:
            print('  Starting OAuth2 flow...')
            print('  A browser window will open for authorization.')
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
            print(f'  ✓ Credentials saved to {TOKEN_FILE}')
    
    return creds


def build_services():
    """Build and return Gmail and Drive service objects."""
    creds = get_credentials()
    
    gmail_service = build('gmail', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    return gmail_service, drive_service


def search_emails(gmail_service):
    """Search for unread emails from specific sender with specific subject."""
    query = f'from:{SENDER_EMAIL} subject:"{SUBJECT_KEYWORD}" is:unread'
    
    try:
        results = gmail_service.users().messages().list(
            userId='me',
            q=query
        ).execute()
        
        messages = results.get('messages', [])
        return messages
    
    except Exception as error:
        print(f'An error occurred while searching emails: {error}')
        return []


def get_email_subject(gmail_service, message_id):
    """Get the subject line of an email for logging purposes."""
    try:
        message = gmail_service.users().messages().get(
            userId='me',
            id=message_id,
            format='metadata',
            metadataHeaders=['Subject']
        ).execute()
        
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'] == 'Subject':
                return header['value']
        
        return 'No Subject'
    
    except Exception as error:
        print(f'Error getting email subject: {error}')
        return 'Unknown'


def get_attachments(gmail_service, message_id):
    """Get PDF attachments from a specific email."""
    try:
        message = gmail_service.users().messages().get(
            userId='me',
            id=message_id
        ).execute()
        
        attachments = []
        
        # Check for attachments in message parts
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['filename'] and part['filename'].lower().endswith('.pdf'):
                    if 'attachmentId' in part['body']:
                        attachment = gmail_service.users().messages().attachments().get(
                            userId='me',
                            messageId=message_id,
                            id=part['body']['attachmentId']
                        ).execute()
                        
                        file_data = base64.urlsafe_b64decode(
                            attachment['data'].encode('UTF-8')
                        )
                        
                        attachments.append({
                            'filename': part['filename'],
                            'data': file_data,
                            'size': part['body'].get('size', 0)
                        })
        
        return attachments
    
    except Exception as error:
        print(f'An error occurred while getting attachments: {error}')
        return []


def upload_to_drive(drive_service, filename, file_data, folder_id):
    """Upload a file to Google Drive."""
    try:
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        media = MediaInMemoryUpload(
            file_data,
            mimetype='application/pdf',
            resumable=True
        )
        
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()
        
        print(f'  ✓ Successfully uploaded: {file.get("name")}')
        print(f'    File ID: {file.get("id")}')
        print(f'    Link: {file.get("webViewLink")}')
        
        return file.get('id')
    
    except Exception as error:
        print(f'  ✗ An error occurred while uploading to Drive: {error}')
        return None


def get_or_create_label(gmail_service, label_name):
    """Get label ID by name, or create it if it doesn't exist."""
    try:
        # Get all labels
        results = gmail_service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        # Check if label exists
        for label in labels:
            if label['name'].lower() == label_name.lower():
                print(f'  ✓ Found existing label: {label_name}')
                return label['id']
        
        # Create new label if it doesn't exist
        label_object = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        
        created_label = gmail_service.users().labels().create(
            userId='me',
            body=label_object
        ).execute()
        
        print(f'  ✓ Created new label: {label_name}')
        return created_label['id']
    
    except Exception as error:
        print(f'  ✗ Error with label: {error}')
        return None


def apply_label_to_email(gmail_service, message_id, label_id):
    """Apply a label to an email message."""
    try:
        gmail_service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'addLabelIds': [label_id]}
        ).execute()
        
        print(f'  ✓ Applied label to message')
        return True
    
    except Exception as error:
        print(f'  ✗ Error applying label: {error}')
        return False


def main():
    """Main function to orchestrate the email to Drive workflow."""
    print('=' * 60)
    print('Gmail to Google Drive PDF Transfer Script')
    print('=' * 60)
    
    # Validate environment variables
    print('\n[0/4] Validating configuration...')
    if not validate_env_variables():
        return
    print('  ✓ Configuration loaded successfully')
    
    print('\n[1/4] Authenticating with OAuth2...')
    try:
        gmail_service, drive_service = build_services()
        print('  ✓ Authentication successful')
    except Exception as e:
        print(f'  ✗ Authentication failed: {e}')
        return
    
    print(f'\n[2/4] Searching for emails...')
    print(f'  From: {SENDER_EMAIL}')
    print(f'  Subject contains: "{SUBJECT_KEYWORD}"')
    print(f'  Status: Unread only')
    
    messages = search_emails(gmail_service)
    
    if not messages:
        print('  No matching unread messages found.')
        return
    
    print(f'  ✓ Found {len(messages)} unread matching message(s)')
    
    # Get or create the label
    print(f'\n[3/4] Setting up Gmail label...')
    label_id = get_or_create_label(gmail_service, GMAIL_LABEL)
    if not label_id:
        print('  ✗ Could not setup label. Continuing without labeling.')
    
    print(f'\n[3.5/4] Processing emails and attachments...')
    
    total_uploaded = 0
    total_attachments = 0
    emails_labeled = 0
    
    for idx, message in enumerate(messages, 1):
        message_id = message['id']
        subject = get_email_subject(gmail_service, message_id)
        
        print(f'\n  Email {idx}/{len(messages)}:')
        print(f'  Subject: {subject}')
        print(f'  Message ID: {message_id}')
        
        attachments = get_attachments(gmail_service, message_id)
        
        if not attachments:
            print('  ⚠ No PDF attachments found')
            # Still label the email even if no attachments
            if label_id and apply_label_to_email(gmail_service, message_id, label_id):
                emails_labeled += 1
            continue
        
        total_attachments += len(attachments)
        email_processed = False
        
        for attachment in attachments:
            size_kb = attachment['size'] / 1024
            print(f'  Found PDF: {attachment["filename"]} ({size_kb:.1f} KB)')
            
            file_id = upload_to_drive(
                drive_service,
                attachment['filename'],
                attachment['data'],
                DRIVE_FOLDER_ID
            )
            
            if file_id:
                total_uploaded += 1
                email_processed = True
        
        # Apply label after processing attachments
        if email_processed and label_id:
            if apply_label_to_email(gmail_service, message_id, label_id):
                emails_labeled += 1
    
    print(f'\n[4/4] Process Complete')
    print('=' * 60)
    print(f'Summary:')
    print(f'  Emails processed: {len(messages)}')
    print(f'  PDF attachments found: {total_attachments}')
    print(f'  PDFs uploaded to Drive: {total_uploaded}')
    print(f'  Emails labeled with "{GMAIL_LABEL}": {emails_labeled}')
    print('=' * 60)


if __name__ == '__main__':
    main()
