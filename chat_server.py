#!/usr/bin/env python3
"""
Chat Server for Gemini File Search Store
-
A Flask API that receives questions and queries a Gemini File Search Store
to provide answers based on uploaded documents.

Usage:
    python chat_server.py [--port PORT]

Environment Variables (in .env):
    FILE_SEARCH_STORE_ID  - Gemini File Search Store ID
    GEMINI_API_KEY        - API key for Gemini
"""

import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
ENV_FILE_PATH = r'C:\Users\acgar\OneDrive\Documents\GoogleAI\.env'
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

If the answer is not in the blog content, say so clearly.

Keep your answers concise but informative."""


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

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=SUBSTACK_SYSTEM_PROMPT,
                tools=[types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[SUBSTACK_STORE_ID]
                    )
                )]
            )
        )

        answer = response.text if response.text else "I'm sorry, I couldn't find an answer to your question."

        return jsonify({'answer': answer})

    except Exception as e:
        print(f'Error processing substack chat request: {e}')
        return jsonify({'error': str(e)}), 500


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
