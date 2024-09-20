import os
os.environ['FLASK_APP'] = 'main.py'

import uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, abort
from werkzeug.utils import secure_filename
from google.cloud import vision
import io
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from flask_migrate import Migrate
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object('config')

# PostgreSQL configuration
db_user = os.environ.get('PGUSER')
db_password = os.environ.get('PGPASSWORD')
db_host = os.environ.get('PGHOST')
db_port = os.environ.get('PGPORT')
db_name = os.environ.get('PGDATABASE')

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require'
app.config['SECRET_KEY'] = os.urandom(24)

# Create engine with connection pool
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], poolclass=QueuePool, pool_size=10, max_overflow=20)

# Initialize SQLAlchemy
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize Google Cloud Vision client
vision_client = vision.ImageAnnotatorClient()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Analysis(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    image_data = db.Column(db.LargeBinary, nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('analyses', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    logger.debug(f"Current user authenticated: {current_user.is_authenticated}")
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    index = request.form.get('index', 0)
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        try:
            file_data = file.read()
            
            # Analyze the image
            image = vision.Image(content=file_data)
            
            # Perform image captioning
            image_context = vision.ImageContext(language_hints=['en'])
            response = vision_client.annotate_image({
                'image': image,
                'features': [{'type_': vision.Feature.Type.LABEL_DETECTION},
                             {'type_': vision.Feature.Type.IMAGE_PROPERTIES},
                             {'type_': vision.Feature.Type.SAFE_SEARCH_DETECTION},
                             {'type_': vision.Feature.Type.WEB_DETECTION},
                             {'type_': vision.Feature.Type.OBJECT_LOCALIZATION},
                             {'type_': vision.Feature.Type.FACE_DETECTION}],
                'image_context': image_context
            })

            # Extract the caption (using label detection as a simple form of captioning)
            caption = ', '.join([label.description for label in response.label_annotations[:3]])

            # Generate a comprehensive description
            description = f"Image Caption: {caption}\n\n"
            description += f"This image contains: {', '.join([label.description for label in response.label_annotations[:5]])}"
            
            # Add color information
            if response.image_properties_annotation.dominant_colors:
                colors = [f"rgb({int(color.color.red)},{int(color.color.green)},{int(color.color.blue)})" 
                          for color in response.image_properties_annotation.dominant_colors.colors[:3]]
                description += f"\nDominant colors: {', '.join(colors)}"

            # Add safe search information
            safe_search = response.safe_search_annotation
            safe_search_results = [f"{attr}: {getattr(safe_search, attr).name}"
                                   for attr in ['adult', 'spoof', 'medical', 'violence', 'racy']
                                   if getattr(safe_search, attr).name not in ['VERY_UNLIKELY', 'UNLIKELY']]
            if safe_search_results:
                description += f"\nContent advisory: {', '.join(safe_search_results)}"

            # Add web entities
            if response.web_detection.web_entities:
                web_entities = [entity.description for entity in response.web_detection.web_entities[:3]]
                description += f"\nRelated web entities: {', '.join(web_entities)}"

            # Add object detection information
            if response.localized_object_annotations:
                object_names = [obj.name for obj in response.localized_object_annotations[:5]]
                description += f"\nDetected objects: {', '.join(object_names)}"

            # Add facial recognition information
            if response.face_annotations:
                face_count = len(response.face_annotations)
                description += f"\nDetected {face_count} face{'s' if face_count > 1 else ''}"
                if face_count > 0:
                    emotions = [emotion for face in response.face_annotations for emotion, likelihood in [
                        ('joy', face.joy_likelihood),
                        ('sorrow', face.sorrow_likelihood),
                        ('anger', face.anger_likelihood),
                        ('surprise', face.surprise_likelihood)
                    ] if likelihood >= vision.Likelihood.LIKELY]
                    if emotions:
                        description += f"\nDetected emotions: {', '.join(emotions)}"
            
            # Save analysis to database
            analysis = Analysis(image_data=file_data, description=description, user_id=current_user.id)
            db.session.add(analysis)
            db.session.commit()
            
            return jsonify({'description': description}), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during file upload and analysis: {str(e)}")
            return jsonify({'error': 'An error occurred during file upload and analysis'}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))
        
        try:
            user = User.query.filter_by(username=username).first()
            if user:
                flash('Username already exists.', 'error')
                return redirect(url_for('register'))
            
            user = User.query.filter_by(email=email).first()
            if user:
                flash('Email already exists.', 'error')
                return redirect(url_for('register'))
            
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'An error occurred during registration: {str(e)}')
            flash(f'An error occurred during registration. Please try again.', 'error')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        logger.debug(f'Login attempt for username: {username}')
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            logger.debug(f'User found: {user.username}')
            if user.check_password(password):
                login_user(user, remember=remember)
                logger.info(f'User {username} logged in successfully')
                flash('Logged in successfully.', 'success')
                return redirect(url_for('index'))
            else:
                logger.warning(f'Invalid password for user: {username}')
                flash('Invalid username or password.', 'error')
        else:
            logger.warning(f'No user found with username: {username}')
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/history')
@login_required
def history():
    analyses = Analysis.query.filter_by(user_id=current_user.id).all()
    return render_template('history.html', analyses=analyses)

@app.route('/image/<image_id>')
@login_required
def serve_image(image_id):
    analysis = Analysis.query.get_or_404(image_id)
    if analysis.user_id != current_user.id:
        abort(403)  # Forbidden
    return send_file(io.BytesIO(analysis.image_data), mimetype='image/jpeg')

def init_db():
    with app.app_context():
        db.create_all()
        logger.info("Database tables created.")

if __name__ == '__main__':
    try:
        init_db()
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
