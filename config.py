import os
import json
import tempfile

# Flask-Uploads configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Google Cloud credentials
credentials_json = os.environ.get('GOOGLE_CLOUD_CREDENTIALS', '')

if credentials_json:
    # Create a temporary file to store the credentials
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        json.dump(json.loads(credentials_json), temp_file)
        temp_file_path = temp_file.name

    # Set the path to the temporary file as the credentials
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file_path
else:
    print("Warning: GOOGLE_CLOUD_CREDENTIALS environment variable is not set.")
