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
import sys
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
ENV_FILE_PATH = r'developmentdirectoragent/.env'

load_dotenv(ENV_FILE_PATH)

# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
FILE_SEARCH_STORE_ID = os.getenv('FILE_SEARCH_STORE_ID')

if not GEMINI_API_KEY or not FILE_SEARCH_STORE_ID:
    print('Error: Missing GEMINI_API_KEY or FILE_SEARCH_STORE_ID in .env')
    sys.exit(1)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests from the frontend

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

# System prompt for the chat
SYSTEM_PROMPT = """You are a helpful assistant for the Joy & Caregiving Foundation and St. Anthony Development and Learning Center.

Your role is to:
- Answer questions about the foundation, its mission, and programs
- Provide information about St. Anthony DLC in the Philippines
- Help visitors understand how they can support or donate
- Be friendly, helpful, and informative

If you don't know the answer based on the available information, politely say so and suggest contacting the foundation directly at jcgfoundation@yahoo.com.

Keep your answers concise but informative. Use a warm, professional tone."""


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


@app.route('/feature-story', methods=['GET'])
def get_feature_story():
    """Query the File Search Store for the feature story JSON.

    Query parameters:
        indexname: (optional) Filter by indexname field in the JSON
        Example: /feature-story?indexname=feature001
    """
    try:
        logger.info('Fetching feature story from File Search Store')

        store_id = FILE_SEARCH_STORE_ID

        if not store_id.startswith('fileSearchStores/'):
            store_id = f'fileSearchStores/{store_id}'

        logger.info(f'Querying store: {store_id}')

        # Get optional indexname parameter
        requested_indexname = request.args.get('indexname', None)
        if requested_indexname:
            logger.info(f'Filtering by indexname: {requested_indexname}')

        # List documents in the store
        response = client.file_search_stores.documents.list(parent=store_id)
        documents = list(response)

        if not documents:
            logger.warning('No documents found in File Search Store')
            return jsonify({'error': 'No documents found in store'}), 404

        logger.info(f'Found {len(documents)} document(s)')

        # Select document: either by indexname or first one
        doc = documents[0]
        display_name = getattr(doc, 'display_name', 'Unknown')
        logger.info(f'Processing document: {display_name}')

        # Use Gemini to extract JSON from the document
        if requested_indexname:
            prompt = f"""Extract the JSON data from the provided document.
Find and return ONLY the JSON object that matches indexname = "{requested_indexname}".
Return ONLY a valid JSON object with these fields:
- title: string
- description: string
- hashtags: array of strings
- youtube_link: string

If the document contains nested JSON, extract the relevant data for the matching indexname.

Return ONLY the valid JSON object, with no markdown formatting, no code blocks, no explanations.
Start with {{ and end with }}"""
        else:
            prompt = """Extract the JSON data from the provided document.
Return ONLY a valid JSON object with these fields:
- title: string
- description: string
- hashtags: array of strings
- youtube_link: string

If the document contains nested JSON (like a 'social_media_post' field), extract the relevant data.

Return ONLY the valid JSON object, with no markdown formatting, no code blocks, no explanations.
Start with { and end with }"""

        logger.info('Using Gemini to extract JSON from File Search Store')

        # Build the full prompt with indexname if provided
        full_prompt = prompt
        if requested_indexname:
            full_prompt = f"{prompt}\n\nIMPORTANT: Find and extract ONLY the story with indexname = '{requested_indexname}'"

        # Use Gemini to extract JSON from the document in the File Search Store
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction="Extract JSON data ONLY from the File Search Store documents provided. Return ONLY valid JSON with title, description, hashtags, and youtube_link fields. Do not use any other knowledge or make up data.",
                tools=[types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store_id]
                    )
                )]
            )
        )

        response_text = response.text.strip()
        logger.debug(f'Gemini response: {response_text[:300]}...')

        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()

        logger.debug(f'Cleaned response: {response_text[:300]}...')

        # Parse the response as JSON
        story_data = json.loads(response_text)

        # Handle nested JSON structure (e.g., {"social_media_post": {...}})
        if 'social_media_post' in story_data:
            story_data = story_data['social_media_post']
            logger.info('Extracted data from social_media_post wrapper')

        # Log what we got
        returned_indexname = story_data.get('indexname', 'NOT FOUND')
        logger.info(f'Returned indexname: "{returned_indexname}"')
        logger.info(f'Requested indexname: "{requested_indexname}"')
        logger.info(f'Full story data keys: {list(story_data.keys())}')

        # Validate indexname if requested (lenient check)
        if requested_indexname:
            returned_indexname_str = str(returned_indexname).strip()
            requested_indexname_str = str(requested_indexname).strip()

            if returned_indexname_str.lower() != requested_indexname_str.lower():
                logger.warning(f'Indexname mismatch - requested "{requested_indexname_str}" but got "{returned_indexname_str}"')
                # Don't fail, just log a warning and return the story anyway
                logger.info('Returning story despite indexname mismatch (lenient mode)')

        logger.info(f'Successfully extracted story: {story_data.get("title", "Unknown")}')

        return jsonify(story_data), 200

    except json.JSONDecodeError as e:
        logger.error(f'Failed to parse JSON response: {str(e)}')
        return jsonify({'error': f'Failed to parse story data as JSON: {str(e)}'}), 500
    except Exception as e:
        logger.error(f'Error in get_feature_story: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'store_id': FILE_SEARCH_STORE_ID
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
    print(f'Using File Search Store: {FILE_SEARCH_STORE_ID}')
    print('Press Ctrl+C to stop')

    app.run(host='0.0.0.0', port=port, debug=True)
