#!/usr/bin/env python3
"""
Chat Server for Gemini File Search Store

A Flask API that receives questions and queries a Gemini File Search Store
to provide answers based on uploaded documents.

Usage:
    python chat_server.py [--port PORT]

Environment Variables (in .env):
    FILE_SEARCH_STORE_ID  - Gemini File Search Store ID
    GEMINI_API_KEY        - API key for Gemini
"""

import os
import re
import sys
import requests as http_requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
ENV_FILE_PATH = r'//var//www//joyandcaregiving//developmentdirectoragent//.env'
load_dotenv(ENV_FILE_PATH)

# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
FILE_SEARCH_STORE_ID = os.getenv('FILE_SEARCH_STORE_ID')
SUBSTACK_STORE_ID = os.getenv('SUBSTACK_STORE_ID')

if not GEMINI_API_KEY or not FILE_SEARCH_STORE_ID:
    print('Error: Missing GEMINI_API_KEY or FILE_SEARCH_STORE_ID in .env')
    sys.exit(1)

if not SUBSTACK_STORE_ID:
    print('Warning: SUBSTACK_STORE_ID not set in .env — /substack endpoint will be unavailable')

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests from the frontend

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

# System prompts
SYSTEM_PROMPT = """You are a helpful assistant for the Joy & Caregiving Foundation and St. Anthony Development and Learning Center.

Your role is to:
- Answer questions about the foundation, its mission, and programs
- Provide information about St. Anthony DLC in the Philippines
- Help visitors understand how they can support or donate
- Be friendly, helpful, and informative

If you don't know the answer based on the available information, politely say so and suggest contacting the foundation directly at jcgfoundation@yahoo.com.

Keep your answers concise but informative. Use a warm, professional tone."""

SUBSTACK_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on Anthony Garcia's Substack blog posts.

Your role is to:
- Answer questions about topics covered in the blog
- Reference specific posts when relevant
- Summarize ideas and insights from the articles
- Be conversational and informative

You can also help users book a meeting with Anthony. If a user wants to schedule
a meeting, call, or appointment, use the request_meeting function. You MUST ask
for any missing required details (their name, preferred date, preferred time,
and how long the meeting should be in minutes) before calling the function.
Also ask if they'd like to include a brief note about what they want to discuss
(this is optional). If they don't provide an email, that's okay — call the
function without it but let them know they won't receive an email confirmation.

If the answer to a non-booking question is not in the blog content, say so clearly.

Keep your answers concise but informative."""

# Gemini function declaration for meeting booking
BOOKING_FUNCTION = types.FunctionDeclaration(
    name='request_meeting',
    description=(
        'Use this function when the user wants to schedule or book a meeting, '
        'call, or appointment with Anthony. Extract the relevant details from '
        'the user message.'
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            'requester_name': types.Schema(
                type=types.Type.STRING,
                description='The name of the person requesting the meeting',
            ),
            'requester_email': types.Schema(
                type=types.Type.STRING,
                description='The email address of the person requesting the meeting',
            ),
            'meeting_date': types.Schema(
                type=types.Type.STRING,
                description='The requested meeting date in ISO format (YYYY-MM-DD)',
            ),
            'meeting_time': types.Schema(
                type=types.Type.STRING,
                description='The requested meeting time in 24-hour format (HH:MM)',
            ),
            'duration_minutes': types.Schema(
                type=types.Type.INTEGER,
                description='The requested meeting duration in minutes',
            ),
            'purpose': types.Schema(
                type=types.Type.STRING,
                description='The purpose or topic of the meeting',
            ),
        },
        required=['requester_name', 'meeting_date', 'meeting_time', 'duration_minutes'],
    ),
)


@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests."""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()

        if not question:
            return jsonify({'error': 'No question provided'}), 400

        # Query the File Search Store using Gemini
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[FILE_SEARCH_STORE_ID]
                    )
                )]
            )
        )

        # Extract the response text
        answer = response.text if response.text else "I'm sorry, I couldn't find an answer to your question."

        return jsonify({'answer': answer})

    except Exception as e:
        print(f'Error processing chat request: {e}')
        return jsonify({'error': str(e)}), 500


# Pattern to detect booking/scheduling intent
_BOOKING_RE = re.compile(
    r'\b(book|schedule|set\s*up)\b.{0,30}\b(meeting|call|appointment|time)\b'
    r'|\b(meet\s+with|book\s+with|book\s+time|schedule\s+time)\b',
    re.IGNORECASE
)


@app.route('/substack', methods=['POST'])
def substack_chat():
    """Handle chat requests against the Substack blog store."""
    if not SUBSTACK_STORE_ID:
        return jsonify({'error': 'Substack store not configured'}), 503

    try:
        data = request.get_json()
        question = data.get('question', '').strip()

        if not question:
            return jsonify({'error': 'No question provided'}), 400

        # The google-genai SDK cannot combine file_search and
        # function_declarations in a single call, so route by intent.
        if _BOOKING_RE.search(question):
            return _handle_substack_booking(question)
        return _handle_substack_question(question)

    except Exception as e:
        print(f'Error processing substack chat request: {e}', file=sys.stderr)
        return jsonify({'error': str(e)}), 500


def _handle_substack_question(question):
    """Answer a blog question using file_search only."""
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=SUBSTACK_SYSTEM_PROMPT,
            tools=[types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[SUBSTACK_STORE_ID]
                )
            )],
        )
    )

    answer = response.text if response.text else "I'm sorry, I couldn't find an answer to your question."
    return jsonify({'answer': answer})


def _handle_substack_booking(question):
    """Handle a booking request using function_declarations only."""
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=SUBSTACK_SYSTEM_PROMPT,
            tools=[types.Tool(
                function_declarations=[BOOKING_FUNCTION]
            )],
        )
    )

    # Check if Gemini returned a function call
    if response.function_calls:
        fc = response.function_calls[0]
        if fc.name == 'request_meeting':
            return _handle_booking_request(dict(fc.args))

    # Gemini returned text instead (e.g. asking for missing details)
    answer = response.text if response.text else "I'd be happy to help you book a meeting. Could you provide your name, preferred date, time, and how long the meeting should be?"
    return jsonify({'answer': answer})


def _handle_booking_request(args):
    """Process a booking function call from Gemini."""
    from booking_manager import create_pending_booking, init_db

    init_db()

    requester_name = args.get('requester_name', 'Unknown')
    requester_email = args.get('requester_email', '')
    meeting_date = args.get('meeting_date', '')
    meeting_time = args.get('meeting_time', '')
    duration = args.get('duration_minutes', 30)
    purpose = args.get('purpose', '')

    try:
        token = create_pending_booking(
            requester_name, requester_email,
            meeting_date, meeting_time,
            duration, purpose
        )

        confirmation_msg = (
            f"I've submitted your meeting request to Anthony. "
            f"Here are the details:\n\n"
            f"- Date: {meeting_date}\n"
            f"- Time: {meeting_time}\n"
            f"- Duration: {duration} minutes\n"
        )
        if purpose:
            confirmation_msg += f"- Purpose: {purpose}\n"

        confirmation_msg += (
            f"\nAnthony will review this request and "
        )
        if requester_email:
            confirmation_msg += f"you'll receive a confirmation email at {requester_email} once it's approved."
        else:
            confirmation_msg += "you'll be notified once it's approved. Since you didn't provide an email, please check back here."

        return jsonify({
            'answer': confirmation_msg,
            'booking_status': 'pending',
            'booking_token': token
        })

    except ValueError as e:
        # Calendar conflict — slot is not available
        return jsonify({
            'answer': str(e),
            'booking_status': 'unavailable'
        })

    except Exception as e:
        print(f'Error creating booking: {e}')
        return jsonify({
            'answer': 'Sorry, I had trouble submitting your meeting request. '
                     'Please try again or contact Anthony directly.',
            'error': str(e)
        }), 500


@app.route('/substack-stats', methods=['GET'])
def substack_stats():
    """Return the total number of Substack posts (proxied to avoid CORS)."""
    substack_url = os.getenv('SUBSTACK_URL', 'https://acgarcia21.substack.com')
    api_url = f'{substack_url}/api/v1/posts'
    post_count = 0
    offset = 0
    limit = 50

    try:
        while True:
            resp = http_requests.get(api_url, params={'limit': limit, 'offset': offset}, timeout=15)
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            post_count += len(batch)
            if len(batch) < limit:
                break
            offset += limit

        return jsonify({'post_count': post_count})

    except Exception as e:
        print(f'Error fetching substack stats: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/approve-booking/<token>', methods=['GET'])
def approve_booking_endpoint(token):
    """Anthony clicks this link from the approval email to approve a meeting."""
    from booking_manager import approve_booking, init_db
    init_db()
    success, message = approve_booking(token)

    if success:
        return f"""
        <html><body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #667eea;">Meeting Approved</h1>
            <p>{message}</p>
            <p>A calendar event has been created and the requester has been notified.</p>
        </body></html>
        """
    else:
        return f"""
        <html><body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #e53e3e;">Could Not Approve</h1>
            <p>{message}</p>
        </body></html>
        """


@app.route('/decline-booking/<token>', methods=['GET'])
def decline_booking_endpoint(token):
    """Anthony clicks this link from the approval email to decline a meeting."""
    from booking_manager import decline_booking, init_db
    init_db()
    decline_booking(token)
    return f"""
    <html><body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
        <h1 style="color: #888;">Meeting Declined</h1>
        <p>The meeting request has been declined.</p>
    </body></html>
    """


@app.route('/booking-status/<token>', methods=['GET'])
def booking_status_endpoint(token):
    """Check the status of a booking by its token."""
    from booking_manager import get_booking_status, init_db
    init_db()
    status = get_booking_status(token)
    if status:
        return jsonify({'status': status})
    return jsonify({'error': 'Booking not found'}), 404


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'store_id': FILE_SEARCH_STORE_ID,
        'substack_store_id': SUBSTACK_STORE_ID
    })


if __name__ == '__main__':
    port = 5000

    # Check for --port argument
    if '--port' in sys.argv:
        try:
            port_index = sys.argv.index('--port') + 1
            port = int(sys.argv[port_index])
        except (IndexError, ValueError):
            print('Invalid port specified, using default 5000')

    print(f'Starting chat server on http://localhost:{port}')
    print(f'  /chat     -> {FILE_SEARCH_STORE_ID}')
    print(f'  /substack -> {SUBSTACK_STORE_ID or "NOT CONFIGURED"}')
    print('Press Ctrl+C to stop')

    app.run(host='0.0.0.0', port=port, debug=True)
