import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file from root or backend directory
basedir = os.path.abspath(os.path.dirname(__file__))
rootdir = os.path.abspath(os.path.join(basedir, '..', '..'))

load_dotenv(os.path.join(rootdir, '.env'), override=True)
load_dotenv(os.path.join(os.path.abspath(os.path.join(basedir, '..')), '.env'), override=True)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-dairymitra-dev-secret-key-32chars')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default-jwt-secret-key-dairymitra-dev-32chars')
    
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_MINUTES', 60)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES_DAYS', 30)))
    
    # Database
    db_url = os.getenv('DATABASE_URL')
    if not db_url or db_url == 'sqlite:///dairymitra.db':
        db_path = os.path.join(basedir, '..', 'dairymitra.db')
        db_url = f'sqlite:///{os.path.abspath(db_path)}'
    elif db_url.startswith('postgres://'):
        # Fix for some PaaS providing postgres:// instead of postgresql://
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mail & OTP
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@dairymitra.com')
    
    OTP_MOCK_MODE = os.getenv('OTP_MOCK_MODE', 'True').lower() in ('true', '1', 't')
    OTP_EXPIRY_MINUTES = int(os.getenv('OTP_EXPIRY_MINUTES', 10))
    OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv('OTP_RESEND_COOLDOWN_SECONDS', 60))
    OTP_MAX_ATTEMPTS = int(os.getenv('OTP_MAX_ATTEMPTS', 5))
    
    # Razorpay
    RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', 'rzp_test_placeholder_key')
    RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', 'rzp_test_placeholder_secret')
    RAZORPAY_WEBHOOK_SECRET = os.getenv('RAZORPAY_WEBHOOK_SECRET', '')
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URI = "memory://"

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    OTP_MOCK_MODE = True
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=10)
    RATELIMIT_ENABLED = False

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
