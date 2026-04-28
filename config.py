import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-prod'
    # Updated to absolute path to avoid confusion
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Persistent Storage Logic (For Azure)
    # If PERSISTENT_STORAGE_PATH env var is set (e.g., /mount/evms_data), use it.
    # Otherwise, fallback to local instance/ and static/uploads/
    PERSISTENT_PATH = os.environ.get('PERSISTENT_STORAGE_PATH')
    
    if PERSISTENT_PATH:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(PERSISTENT_PATH, "evms.db")}'
        UPLOAD_FOLDER = os.path.join(PERSISTENT_PATH, 'uploads')
    else:
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'evms.db')
        UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email Configuration (SMTP)
    SMTP_SERVER = os.environ.get('SMTP_SERVER')
    SMTP_PORT = os.environ.get('SMTP_PORT') or 587
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS') or 'True'
    SENDER_EMAIL_ADDRESS = os.environ.get('SENDER_EMAIL_ADDRESS') or "noreply@yourdomain.com"
