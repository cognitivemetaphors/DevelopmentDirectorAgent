#!/usr/bin/env python3
"""
Booking Manager — handles meeting request approvals, Google Calendar
event creation, and email notifications via Gmail API.

Used by chat_server.py to support human-in-the-loop meeting booking
through the /substack chat interface.
"""

import os
import uuid
import json
import sqlite3
import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables
ENV_FILE_PATH = r'//var//www//joyandcaregiving//developmentdirectoragent//.env'
load_dotenv(ENV_FILE_PATH)

# Configuration
TOKEN_FILE = os.getenv('TOKEN_FILE')
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE')
DB_PATH = os.getenv('DB_PATH', '/var/www/cognitivemetaphors/bookings.db')
SERVER_BASE_URL = os.getenv('SERVER_BASE_URL', 'http://143.42.1.253:5000')
OWNER_EMAIL = 'acgarcia21@gmail.com'
CALENDAR_ID = 'primary'

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/calendar',
]


def _get_credentials():
    """Load OAuth credentials from token.json, refresh if needed."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        else:
            raise RuntimeError(
                'OAuth token is missing or cannot be refreshed. '
                'Run get_token.py on a machine with a browser.'
            )
    return creds


def _get_gmail_service():
    return build('gmail', 'v1', credentials=_get_credentials())


def _get_calendar_service():
    return build('calendar', 'v3', credentials=_get_credentials())


def init_db():
    """Create the bookings table if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        approval_token TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        requester_name TEXT,
        requester_email TEXT,
        meeting_date TEXT NOT NULL,
        meeting_time TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL,
        purpose TEXT,
        created_at TEXT NOT NULL,
        approved_at TEXT,
        calendar_event_id TEXT
    )''')
    conn.commit()
    conn.close()


def check_calendar_availability(meeting_date, meeting_time, duration_minutes):
    """
    Check if Anthony's calendar is free for the requested time slot.
    Returns (is_free: bool, conflict_summary: str or None).
    """
    from zoneinfo import ZoneInfo
    eastern = ZoneInfo('America/New_York')
    start_dt = datetime.fromisoformat(f'{meeting_date}T{meeting_time}:00').replace(tzinfo=eastern)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    body = {
        'timeMin': start_dt.isoformat(),
        'timeMax': end_dt.isoformat(),
        'timeZone': 'America/New_York',
        'items': [{'id': CALENDAR_ID}],
    }

    result = _get_calendar_service().freebusy().query(body=body).execute()
    busy_slots = result.get('calendars', {}).get(CALENDAR_ID, {}).get('busy', [])

    if busy_slots:
        return False, f'Anthony already has an event from {busy_slots[0]["start"]} to {busy_slots[0]["end"]}.'
    return True, None


def create_pending_booking(requester_name, requester_email, meeting_date,
                           meeting_time, duration_minutes, purpose=''):
    """
    Store a pending booking and send an approval email to Anthony.
    Checks calendar availability first. Raises ValueError if slot is busy.
    Returns the approval_token for reference.
    """
    is_free, conflict = check_calendar_availability(
        meeting_date, meeting_time, duration_minutes
    )
    if not is_free:
        raise ValueError(
            f'That time slot is not available. {conflict} '
            f'Please try a different date or time.'
        )

    approval_token = uuid.uuid4().hex
    now = datetime.utcnow().isoformat()

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        '''INSERT INTO bookings
           (approval_token, status, requester_name, requester_email,
            meeting_date, meeting_time, duration_minutes, purpose, created_at)
           VALUES (?, 'pending', ?, ?, ?, ?, ?, ?, ?)''',
        (approval_token, requester_name, requester_email,
         meeting_date, meeting_time, duration_minutes, purpose, now)
    )
    conn.commit()
    conn.close()

    _send_approval_email(approval_token, requester_name, requester_email,
                         meeting_date, meeting_time, duration_minutes, purpose)

    return approval_token


def approve_booking(approval_token):
    """
    Approve a pending booking: create calendar event, send confirmation.
    Returns (success: bool, message: str).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        'SELECT * FROM bookings WHERE approval_token = ?',
        (approval_token,)
    ).fetchone()

    if not row:
        conn.close()
        return False, 'Booking not found.'

    if row['status'] != 'pending':
        conn.close()
        return False, f'Booking already {row["status"]}.'

    event_id = _create_calendar_event(
        row['requester_name'], row['requester_email'],
        row['meeting_date'], row['meeting_time'],
        row['duration_minutes'], row['purpose']
    )

    now = datetime.utcnow().isoformat()
    conn.execute(
        '''UPDATE bookings
           SET status = 'approved', approved_at = ?, calendar_event_id = ?
           WHERE approval_token = ?''',
        (now, event_id, approval_token)
    )
    conn.commit()
    conn.close()

    if row['requester_email']:
        _send_confirmation_email(
            row['requester_email'], row['requester_name'],
            row['meeting_date'], row['meeting_time'],
            row['duration_minutes'], row['purpose']
        )

    return True, 'Booking approved and calendar event created.'


def decline_booking(approval_token):
    """Decline a pending booking."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE bookings SET status = 'declined' WHERE approval_token = ? AND status = 'pending'",
        (approval_token,)
    )
    conn.commit()
    conn.close()


def get_booking_status(approval_token):
    """Return the status string for a booking, or None if not found."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        'SELECT status FROM bookings WHERE approval_token = ?',
        (approval_token,)
    ).fetchone()
    conn.close()
    return row['status'] if row else None


def _send_approval_email(token, name, email, date, time, duration, purpose):
    """Send approval request email to Anthony via Gmail API."""
    approve_url = f'{SERVER_BASE_URL}/approve-booking/{token}'
    decline_url = f'{SERVER_BASE_URL}/decline-booking/{token}'

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #667eea;">New Meeting Request</h2>
        <table style="border-collapse: collapse; width: 100%;">
            <tr><td style="padding: 8px; font-weight: bold;">From:</td>
                <td style="padding: 8px;">{name} ({email or 'no email provided'})</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Date:</td>
                <td style="padding: 8px;">{date}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Time:</td>
                <td style="padding: 8px;">{time}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Duration:</td>
                <td style="padding: 8px;">{duration} minutes</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Purpose:</td>
                <td style="padding: 8px;">{purpose or 'Not specified'}</td></tr>
        </table>
        <br>
        <a href="{approve_url}"
           style="background: #667eea; color: white; padding: 12px 24px;
                  text-decoration: none; border-radius: 6px; font-weight: bold;
                  display: inline-block; margin-right: 12px;">
            Approve Meeting
        </a>
        <a href="{decline_url}"
           style="background: #e53e3e; color: white; padding: 12px 24px;
                  text-decoration: none; border-radius: 6px; font-weight: bold;
                  display: inline-block;">
            Decline
        </a>
    </div>
    """

    message = MIMEText(html_body, 'html')
    message['to'] = OWNER_EMAIL
    message['subject'] = f'Meeting Request from {name} - {date} at {time}'

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    _get_gmail_service().users().messages().send(
        userId='me', body={'raw': raw}
    ).execute()


def _create_calendar_event(name, email, date_str, time_str, duration, purpose):
    """Create a Google Calendar event and return the event ID."""
    start_dt = datetime.fromisoformat(f'{date_str}T{time_str}:00')
    end_dt = start_dt + timedelta(minutes=duration)

    event_body = {
        'summary': f'Meeting with {name}',
        'description': f'Purpose: {purpose or "N/A"}\nRequester email: {email or "N/A"}',
        'start': {
            'dateTime': start_dt.isoformat(),
            'timeZone': 'America/New_York',
        },
        'end': {
            'dateTime': end_dt.isoformat(),
            'timeZone': 'America/New_York',
        },
    }

    if email:
        event_body['attendees'] = [{'email': email}]

    event = _get_calendar_service().events().insert(
        calendarId=CALENDAR_ID, body=event_body, sendUpdates='all'
    ).execute()

    return event.get('id')


def _send_confirmation_email(to_email, name, date, time, duration, purpose):
    """Send confirmation email to the requester."""
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #667eea;">Your meeting with Anthony has been confirmed!</h2>
        <table style="border-collapse: collapse; width: 100%;">
            <tr><td style="padding: 8px; font-weight: bold;">Date:</td>
                <td style="padding: 8px;">{date}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Time:</td>
                <td style="padding: 8px;">{time} (Eastern Time)</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Duration:</td>
                <td style="padding: 8px;">{duration} minutes</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Purpose:</td>
                <td style="padding: 8px;">{purpose or 'Not specified'}</td></tr>
        </table>
        <p>You should also receive a Google Calendar invitation shortly.</p>
        <p>Looking forward to speaking with you!</p>
    </div>
    """

    message = MIMEText(html_body, 'html')
    message['to'] = to_email
    message['subject'] = f'Meeting Confirmed - {date} at {time}'

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    _get_gmail_service().users().messages().send(
        userId='me', body={'raw': raw}
    ).execute()
