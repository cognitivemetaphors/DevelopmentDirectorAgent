#!/usr/bin/env python3
"""
Chat Server for Gemini File Search Store

A Flask API that receives questions and queries a Gemini File Search Store
to provide answers based on uploaded documents.

Usage:
    python chat_server2.py [--port PORT]

Environment Variables (in .env):
    FILE_SEARCH_STORE_ID  - Gemini File Search Store ID
    GEMINI_API_KEY        - API key for Gemini
    FEATURED_STORY_INDEXNAME - Featured story indexname
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

# Configuration variables (will be reloaded before each request)
GEMINI_API_KEY = None
FILE_SEARCH_STORE_ID = None
FEATURED_STORY_INDEXNAME = ''

def reload_env_config():
    """Reload environment variables from .env file before each request."""
    global GEMINI_API_KEY, FILE_SEARCH_STORE_ID, FEATURED_STORY_INDEXNAME

    # Reload the .env file
    load_dotenv(ENV_FILE_PATH, override=True)

    # Update configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    FILE_SEARCH_STORE_ID = os.getenv('FILE_SEARCH_STORE_ID')
    FEATURED_STORY_INDEXNAME = os.getenv('FEATURED_STORY_INDEXNAME', '')

    logger.debug(f'Reloaded env config: FEATURED_STORY_INDEXNAME={FEATURED_STORY_INDEXNAME}')

# Load initial configuration
reload_env_config()

if not GEMINI_API_KEY or not FILE_SEARCH_STORE_ID:
    print('Error: Missing GEMINI_API_KEY or FILE_SEARCH_STORE_ID in .env')
    sys.exit(1)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Reload environment variables before every request
@app.before_request
def before_request():
    """Reload env config before each request."""
    reload_env_config()
    # Update Gemini client with latest API key
    global client
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)

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

# System prompt specifically for feature story extraction
FEATURE_STORY_SYSTEM_PROMPT = """You are a data extraction assistant for the Joy & Caregiving Foundation and St. Anthony Development and Learning Center.

Your role is to:
- Extract structured information about features from the available documents
- Provide exact titles, descriptions, hashtags, and media links as they appear
- Format the data clearly and consistently
- Include all available information, including links to external resources

When providing information:
- Always include the exact title as written
- Provide accurate descriptions from the source material
- List all hashtags associated with the feature
- Include image filenames and video/media URLs as found in the documents
- If a field is not available, respond with "none"

Be precise, thorough, and provide complete information without omission."""


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
        logger.error(f'Error processing chat request: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/feature-story', methods=['GET'])
def get_feature_story():
    """Load feature story from local JSON files in the data directory.

    Query parameters:
        indexname: (optional) Specify which feature to load
        If not provided, uses FEATURED_STORY_INDEXNAME from .env
        Example: /feature-story?indexname=feature001
    """
    try:
        logger.info('Fetching feature story from local data directory')

        # Get optional indexname parameter, or use default from .env
        requested_indexname = request.args.get('indexname')
        if not requested_indexname:
            requested_indexname = FEATURED_STORY_INDEXNAME

        if not requested_indexname:
            logger.warning('No indexname provided and FEATURED_STORY_INDEXNAME not set in .env')
            return jsonify({'error': 'No feature story indexname specified'}), 400

        logger.info(f'Loading feature story: {requested_indexname}')

        # Try to find the JSON file for this feature
        # Look in the data directory for a file matching the indexname
        data_dir = '/var/www/joyandcaregiving/data'
        feature_file = os.path.join(data_dir, f'{requested_indexname}.json')

        # Also try looking for features.json with an array and search within
        features_file = os.path.join(data_dir, 'features.json')

        story_data = None

        # First, try individual feature file
        if os.path.exists(feature_file):
            logger.info(f'Found individual feature file: {feature_file}')
            try:
                with open(feature_file, 'r', encoding='utf-8') as f:
                    story_data = json.load(f)
                    # Ensure indexname is set
                    if 'indexname' not in story_data:
                        story_data['indexname'] = requested_indexname
                    logger.info(f'Successfully loaded feature from {feature_file}')
            except Exception as e:
                logger.error(f'Error reading {feature_file}: {str(e)}')

        # If not found, try features.json (array format)
        if not story_data and os.path.exists(features_file):
            logger.info(f'Checking features array in {features_file}')
            try:
                with open(features_file, 'r', encoding='utf-8') as f:
                    features_array = json.load(f)
                    if isinstance(features_array, list):
                        # Search for matching indexname
                        story_data = next((f for f in features_array if f.get('indexname') == requested_indexname), None)
                        if story_data:
                            logger.info(f'Found feature {requested_indexname} in features array')
                    elif isinstance(features_array, dict):
                        # Check if features_array has a 'features' key with an array
                        if 'features' in features_array and isinstance(features_array['features'], list):
                            story_data = next((f for f in features_array['features'] if f.get('indexname') == requested_indexname), None)
                            if story_data:
                                logger.info(f'Found feature {requested_indexname} in features.features array')
            except Exception as e:
                logger.error(f'Error reading {features_file}: {str(e)}')

        if not story_data:
            logger.warning(f'Feature {requested_indexname} not found in data directory')
            return jsonify({'error': f'Feature "{requested_indexname}" not found'}), 404

        # Flatten nested structure - if data is nested in social_media_post, extract it
        if 'social_media_post' in story_data and isinstance(story_data['social_media_post'], dict):
            social_post = story_data['social_media_post']
            # Use nested data if root level is null
            if not story_data.get('title') and social_post.get('title'):
                story_data['title'] = social_post['title']
            if not story_data.get('description') and social_post.get('description'):
                story_data['description'] = social_post['description']
            if not story_data.get('hashtags') and social_post.get('hashtags'):
                story_data['hashtags'] = social_post['hashtags']
            if not story_data.get('image_link') and social_post.get('image_link'):
                story_data['image_link'] = social_post['image_link']
            if not story_data.get('youtube_link') and social_post.get('youtube_link'):
                story_data['youtube_link'] = social_post['youtube_link']

        # Ensure all expected fields are present
        story_data.setdefault('indexname', requested_indexname)
        story_data.setdefault('title', None)
        story_data.setdefault('description', None)
        story_data.setdefault('hashtags', None)
        story_data.setdefault('image_link', None)
        story_data.setdefault('youtube_link', None)

        # Remove nested social_media_post to return clean data to frontend
        story_data.pop('social_media_post', None)

        logger.info(f'Successfully loaded story: {story_data.get("title", "Unknown")}')
        return jsonify(story_data), 200

    except Exception as e:
        logger.error(f'Error in get_feature_story: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/test-gemini', methods=['GET'])
def test_gemini():
    """Test endpoint to verify Gemini API is working without file_search.

    This helps diagnose if the issue is with file_search tool or the general API.
    """
    try:
        logger.info('Testing Gemini API without file_search tool')

        # Simple test without file_search
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Say "Hello, testing Gemini API"',
        )

        logger.warning(f'TEST RESPONSE TYPE: {type(response).__name__}')
        logger.warning(f'TEST RESPONSE.TEXT: {repr(response.text)}')

        if response.text:
            return jsonify({
                'status': 'success',
                'message': 'Gemini API is working',
                'response': response.text[:200]
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Gemini API returned no text even without file_search'
            }), 500
    except Exception as e:
        logger.error(f'Error testing Gemini: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/config', methods=['GET'])
def get_config():
    """Return frontend configuration."""
    featured_story_indexname = os.getenv('FEATURED_STORY_INDEXNAME', '')
    return jsonify({
        'featured_story_indexname': featured_story_indexname
    })


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
