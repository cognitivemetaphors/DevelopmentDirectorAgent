#!/usr/bin/env python3
"""
Peloton Exercise Data Export Script

Pulls workout history and metrics from Peloton's API and exports to
a local JSON file and a Google Sheets spreadsheet.

Usage:
    python peloton_export.py [--verbose] [--json-only] [--sheets-only]

Environment Variables (in .env):
    PELOTON_BEARER_TOKEN   - Bearer token from browser DevTools
    PELOTON_USER_ID        - Your Peloton user ID
    PELOTON_SPREADSHEET_ID - Google Sheets spreadsheet ID
    TOKEN_FILE             - Path to OAuth token cache
    CREDENTIALS_FILE       - Path to OAuth credentials JSON
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from collections import defaultdict

import base64
import requests
from dotenv import load_dotenv
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# === CONFIGURATION ===
ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
PELOTON_BASE_URL = 'https://api.onepeloton.com'
JSON_OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'peloton_export.json')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Export Peloton exercise data to JSON and Google Sheets'
    )
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable debug logging')
    parser.add_argument('--json-only', action='store_true', help='Skip Google Sheets update')
    parser.add_argument('--sheets-only', action='store_true', help='Skip JSON export, use existing JSON')
    return parser.parse_args()


def setup_logging(verbose=False):
    """Configure logging."""
    log_level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.addHandler(handler)

    return logging.getLogger(__name__)


def validate_env(sheets_needed=True):
    """Validate required environment variables."""
    required = {
        'PELOTON_BEARER_TOKEN': os.getenv('PELOTON_BEARER_TOKEN'),
    }
    if sheets_needed:
        required['PELOTON_SPREADSHEET_ID'] = os.getenv('PELOTON_SPREADSHEET_ID')
        required['TOKEN_FILE'] = os.getenv('TOKEN_FILE')
        required['CREDENTIALS_FILE'] = os.getenv('CREDENTIALS_FILE')

    missing = [k for k, v in required.items() if not v]
    if missing:
        logger.error(f'Missing required environment variables: {missing}')
        return False
    return True


# ── Peloton API ──────────────────────────────────────────────────────

def _extract_user_id_from_jwt(token):
    """Extract the Peloton user_id from a JWT bearer token."""
    try:
        # JWT is 3 base64 segments separated by dots; payload is the second
        payload_b64 = token.split('.')[1]
        # Add padding if needed
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        user_id = payload.get('http://onepeloton.com/user_id', '')
        if user_id:
            return user_id
    except Exception:
        pass
    return None


def peloton_session(bearer_token):
    """Create an authenticated Peloton session using a bearer token.

    The user_id is auto-extracted from the JWT token.

    To get your bearer token:
    1. Log into members.onepeloton.com in your browser
    2. Open DevTools (F12) > Network tab
    3. Click any link, find a request to api.onepeloton.com
    4. Copy the 'Authorization: Bearer <token>' value from request headers
    """
    # Extract user_id from the JWT
    user_id = _extract_user_id_from_jwt(bearer_token)
    if not user_id:
        raise ValueError('Could not extract user_id from bearer token. Token may be invalid.')

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'peloton_export/1.0',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {bearer_token}',
        'Peloton-Platform': 'web',
    })

    # Verify the token works
    resp = session.get(f'{PELOTON_BASE_URL}/api/me')
    resp.raise_for_status()
    logger.info(f'Authenticated as user {user_id}')
    return session, user_id


def fetch_all_workouts(session, user_id):
    """Fetch all workouts (paginated)."""
    workouts = []
    page = 0
    limit = 50

    while True:
        url = f'{PELOTON_BASE_URL}/api/user/{user_id}/workouts'
        resp = session.get(url, params={'limit': limit, 'page': page, 'joins': 'ride,ride.instructor'})
        resp.raise_for_status()
        data = resp.json()

        batch = data.get('data', [])
        if not batch:
            break

        workouts.extend(batch)
        logger.debug(f'Fetched page {page} — {len(batch)} workouts')

        total = data.get('total', 0)
        if len(workouts) >= total:
            break

        page += 1
        time.sleep(0.3)  # Be polite to the API

    logger.info(f'Fetched {len(workouts)} total workouts')
    return workouts


def fetch_workout_metrics(session, workout_id):
    """Fetch performance metrics for a single workout."""
    try:
        url = f'{PELOTON_BASE_URL}/api/workout/{workout_id}/performance_graph'
        resp = session.get(url, params={'every_n': 60})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.debug(f'Could not fetch metrics for {workout_id}: {e}')
        return None


def fetch_user_overview(session, user_id):
    """Fetch user overview/summary stats."""
    url = f'{PELOTON_BASE_URL}/api/user/{user_id}/overview'
    resp = session.get(url)
    resp.raise_for_status()
    return resp.json()


def extract_workout_row(workout, metrics):
    """Extract a flat dict of useful fields from a workout + its metrics."""
    ride = workout.get('ride') or {}
    instructor = ride.get('instructor') or {}

    start_epoch = workout.get('start_time', 0)
    start_dt = datetime.fromtimestamp(start_epoch) if start_epoch else None

    # Pull summary values from the workout object
    row = {
        'id': workout.get('id', ''),
        'date': start_dt.strftime('%Y-%m-%d') if start_dt else '',
        'time': start_dt.strftime('%H:%M') if start_dt else '',
        'type': workout.get('fitness_discipline', ''),
        'title': ride.get('title', workout.get('title', '')),
        'instructor': instructor.get('name', ''),
        'duration_min': '',
        'total_output_kj': workout.get('total_work', 0) / 1000 if workout.get('total_work') else '',
        'distance_mi': round(workout.get('distance', 0) or 0, 2),
        'calories': workout.get('calories', '') or '',
        'avg_heart_rate': '',
        'max_heart_rate': '',
        'avg_cadence': '',
        'avg_resistance': '',
        'avg_speed': '',
        'difficulty': ride.get('difficulty_rating_avg', ''),
        'rating': ride.get('overall_rating_avg', ''),
    }

    # Fix duration
    ride_duration = (workout.get('ride') or {}).get('duration', 0)
    if ride_duration:
        row['duration_min'] = round(ride_duration / 60)
    elif workout.get('start_time') and workout.get('end_time'):
        row['duration_min'] = round((workout['end_time'] - workout['start_time']) / 60)
    else:
        row['duration_min'] = ''

    # Total output formatting
    if workout.get('total_work'):
        row['total_output_kj'] = round(workout['total_work'] / 1000, 1)
    else:
        row['total_output_kj'] = ''

    # Extract averages from metrics
    if metrics:
        summaries = {s['slug']: s for s in metrics.get('summaries', [])}
        avg_summaries = {s['slug']: s for s in metrics.get('average_summaries', [])}

        if 'heart_rate' in avg_summaries:
            row['avg_heart_rate'] = avg_summaries['heart_rate'].get('value', '')
        if 'heart_rate' in summaries:
            # Max HR from the max in the metrics data
            hr_values = []
            for m in metrics.get('metrics', []):
                if m.get('slug') == 'heart_rate':
                    hr_values = m.get('values', [])
                    break
            if hr_values:
                row['max_heart_rate'] = max(hr_values)

        if 'cadence' in avg_summaries:
            row['avg_cadence'] = avg_summaries['cadence'].get('value', '')
        if 'resistance' in avg_summaries:
            row['avg_resistance'] = avg_summaries['resistance'].get('value', '')
        if 'speed' in avg_summaries:
            row['avg_speed'] = avg_summaries['speed'].get('value', '')

    return row


# ── JSON Export ──────────────────────────────────────────────────────

def save_to_json(data, filepath):
    """Write export data to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    logger.info(f'Saved data to {filepath}')


def load_from_json(filepath):
    """Load previously exported data from JSON."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


# ── Google Sheets ────────────────────────────────────────────────────

def get_google_credentials():
    """Get valid Google OAuth credentials (reuses token.json pattern)."""
    token_file = os.getenv('TOKEN_FILE')
    credentials_file = os.getenv('CREDENTIALS_FILE')
    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info('Refreshing Google OAuth token...')
            creds.refresh(GoogleRequest())
        else:
            logger.info('Starting OAuth2 flow (browser will open)...')
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, 'w') as f:
            f.write(creds.to_json())
            logger.info(f'Credentials saved to {token_file}')

    return creds


def write_to_sheets(creds, spreadsheet_id, workout_rows, overview):
    """Write 3 tabs to Google Sheets: Workouts, Summary, Performance Trends."""
    service = build('sheets', 'v4', credentials=creds)
    sheets = service.spreadsheets()

    # Ensure the 3 tabs exist
    _ensure_tabs(sheets, spreadsheet_id, ['Workouts', 'Summary', 'Performance Trends'])

    # Tab 1: Workouts
    headers = [
        'Date', 'Time', 'Type', 'Title', 'Instructor', 'Duration (min)',
        'Output (kJ)', 'Distance (mi)', 'Calories', 'Avg HR', 'Max HR',
        'Avg Cadence', 'Avg Resistance', 'Avg Speed', 'Difficulty', 'Rating'
    ]
    rows = [headers]
    for w in workout_rows:
        rows.append([
            w['date'], w['time'], w['type'], w['title'], w['instructor'],
            w['duration_min'], w['total_output_kj'], w['distance_mi'],
            w['calories'], w['avg_heart_rate'], w['max_heart_rate'],
            w['avg_cadence'], w['avg_resistance'], w['avg_speed'],
            w['difficulty'], w['rating'],
        ])

    _clear_and_write(sheets, spreadsheet_id, 'Workouts', rows)
    logger.info(f'Wrote {len(workout_rows)} rows to Workouts tab')

    # Tab 2: Summary
    summary_rows = _build_summary(workout_rows, overview)
    _clear_and_write(sheets, spreadsheet_id, 'Summary', summary_rows)
    logger.info('Wrote Summary tab')

    # Tab 3: Performance Trends
    trends_rows = _build_trends(workout_rows)
    _clear_and_write(sheets, spreadsheet_id, 'Performance Trends', trends_rows)
    logger.info('Wrote Performance Trends tab')


def _ensure_tabs(sheets, spreadsheet_id, tab_names):
    """Create tabs if they don't already exist."""
    meta = sheets.get(spreadsheetId=spreadsheet_id).execute()
    existing = {s['properties']['title'] for s in meta.get('sheets', [])}

    requests_body = []
    for name in tab_names:
        if name not in existing:
            requests_body.append({
                'addSheet': {'properties': {'title': name}}
            })

    if requests_body:
        sheets.batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests_body}
        ).execute()
        logger.debug(f'Created tabs: {[r["addSheet"]["properties"]["title"] for r in requests_body]}')


def _clear_and_write(sheets, spreadsheet_id, tab_name, rows):
    """Clear a tab and write rows."""
    sheets.values().clear(
        spreadsheetId=spreadsheet_id,
        range=f'{tab_name}!A:Z'
    ).execute()

    sheets.values().update(
        spreadsheetId=spreadsheet_id,
        range=f'{tab_name}!A1',
        valueInputOption='RAW',
        body={'values': rows}
    ).execute()


def _build_summary(workout_rows, overview):
    """Build summary tab data."""
    rows = [['Metric', 'Value']]

    total = len(workout_rows)
    total_calories = sum(w['calories'] for w in workout_rows if isinstance(w['calories'], (int, float)))
    total_distance = sum(w['distance_mi'] for w in workout_rows if isinstance(w['distance_mi'], (int, float)))
    total_output = sum(w['total_output_kj'] for w in workout_rows if isinstance(w['total_output_kj'], (int, float)))

    # Workouts by type
    type_counts = defaultdict(int)
    for w in workout_rows:
        if w['type']:
            type_counts[w['type']] += 1
    type_str = ', '.join(f'{k}: {v}' for k, v in sorted(type_counts.items(), key=lambda x: -x[1]))

    dates = [w['date'] for w in workout_rows if w['date']]
    first_workout = min(dates) if dates else 'N/A'
    last_workout = max(dates) if dates else 'N/A'

    rows.append(['Total Workouts', total])
    rows.append(['Total Calories', round(total_calories)])
    rows.append(['Total Distance (mi)', round(total_distance, 1)])
    rows.append(['Total Output (kJ)', round(total_output, 1)])
    rows.append(['Workouts by Type', type_str])
    rows.append(['First Workout', first_workout])
    rows.append(['Last Workout', last_workout])

    # Add overview stats if available
    if overview and isinstance(overview, dict):
        for category in overview.get('workout_counts', []):
            if isinstance(category, dict):
                name = category.get('name', '')
                count = category.get('count', 0)
                if name and count:
                    rows.append([f'Peloton {name} Count', count])

    return rows


def _build_trends(workout_rows):
    """Build monthly performance trends."""
    monthly = defaultdict(lambda: {
        'workouts': 0, 'calories': 0, 'output': 0, 'hr_sum': 0, 'hr_count': 0, 'distance': 0
    })

    for w in workout_rows:
        if not w['date']:
            continue
        month = w['date'][:7]  # YYYY-MM
        m = monthly[month]
        m['workouts'] += 1
        if isinstance(w['calories'], (int, float)):
            m['calories'] += w['calories']
        if isinstance(w['total_output_kj'], (int, float)):
            m['output'] += w['total_output_kj']
        if isinstance(w['avg_heart_rate'], (int, float)) and w['avg_heart_rate'] > 0:
            m['hr_sum'] += w['avg_heart_rate']
            m['hr_count'] += 1
        if isinstance(w['distance_mi'], (int, float)):
            m['distance'] += w['distance_mi']

    headers = ['Month', 'Workouts', 'Total Calories', 'Total Output (kJ)', 'Avg HR', 'Total Distance (mi)']
    rows = [headers]

    for month in sorted(monthly.keys(), reverse=True):
        m = monthly[month]
        avg_hr = round(m['hr_sum'] / m['hr_count'], 1) if m['hr_count'] else ''
        rows.append([
            month, m['workouts'], round(m['calories']),
            round(m['output'], 1), avg_hr, round(m['distance'], 2)
        ])

    return rows


# ── Main ─────────────────────────────────────────────────────────────

def main():
    global logger

    if not os.path.exists(ENV_FILE_PATH):
        print(f'Error: .env file not found at: {ENV_FILE_PATH}')
        return 1

    load_dotenv(ENV_FILE_PATH)

    args = parse_arguments()
    logger = setup_logging(args.verbose)

    sheets_needed = not args.json_only
    if not validate_env(sheets_needed=sheets_needed):
        return 1

    # If --sheets-only, load from existing JSON
    if args.sheets_only:
        if not os.path.exists(JSON_OUTPUT_FILE):
            logger.error(f'No existing JSON file found at {JSON_OUTPUT_FILE}. Run without --sheets-only first.')
            return 1
        logger.info(f'Loading data from {JSON_OUTPUT_FILE}')
        data = load_from_json(JSON_OUTPUT_FILE)
        workout_rows = data.get('workouts', [])
        overview = data.get('overview', {})
    else:
        # [1/4] Authenticate with Peloton
        logger.info('[1/4] Authenticating with Peloton...')
        try:
            session, user_id = peloton_session(
                os.getenv('PELOTON_BEARER_TOKEN')
            )
        except Exception as e:
            logger.error(f'Peloton login failed: {e}')
            return 1

        # [2/4] Fetch workouts and metrics
        logger.info('[2/4] Fetching workouts...')
        try:
            raw_workouts = fetch_all_workouts(session, user_id)
        except Exception as e:
            logger.error(f'Failed to fetch workouts: {e}')
            return 1

        logger.info('[2/4] Fetching overview stats...')
        try:
            overview = fetch_user_overview(session, user_id)
        except Exception as e:
            logger.warning(f'Could not fetch overview: {e}')
            overview = {}

        logger.info('[2/4] Fetching per-workout metrics...')
        workout_rows = []
        for i, workout in enumerate(raw_workouts):
            wid = workout.get('id', '')
            metrics = fetch_workout_metrics(session, wid)
            row = extract_workout_row(workout, metrics)
            workout_rows.append(row)

            if (i + 1) % 50 == 0:
                logger.info(f'  Processed {i + 1}/{len(raw_workouts)} workouts...')
            time.sleep(0.2)  # Rate limiting

        # Sort by date descending
        workout_rows.sort(key=lambda w: w.get('date', ''), reverse=True)
        logger.info(f'Processed {len(workout_rows)} workouts')

        # [3/4] Save to JSON
        if not args.sheets_only:
            logger.info('[3/4] Saving to JSON...')
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'total_workouts': len(workout_rows),
                'overview': overview,
                'workouts': workout_rows,
            }
            save_to_json(export_data, JSON_OUTPUT_FILE)

    # [4/4] Update Google Sheets
    if not args.json_only:
        logger.info('[4/4] Updating Google Sheets...')
        try:
            creds = get_google_credentials()
            spreadsheet_id = os.getenv('PELOTON_SPREADSHEET_ID')
            write_to_sheets(creds, spreadsheet_id, workout_rows, overview)
            logger.info('Google Sheets updated successfully')
        except Exception as e:
            logger.error(f'Failed to update Google Sheets: {e}')
            return 1
    else:
        logger.info('Skipping Google Sheets (--json-only)')

    logger.info('Export complete!')
    return 0


if __name__ == '__main__':
    sys.exit(main())
