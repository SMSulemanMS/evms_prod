from extensions import db
from flask_login import UserMixin
from datetime import datetime

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False) # Plain text for simplicity as requested, or hashed

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    location_url = db.Column(db.String(500))
    location_text = db.Column(db.String(200)) # e.g. "Sheraton Grand Doha"
    description = db.Column(db.Text)
    date_time = db.Column(db.DateTime, nullable=False)
    banner_filename = db.Column(db.String(200)) # Stored locally
    logo_filename = db.Column(db.String(200))   # Stored locally
    agenda = db.Column(db.Text)
    url_slug = db.Column(db.String(100), unique=True) # Unique identifier for the event URL
    status = db.Column(db.String(20), default='Published')
    partner_logo_1 = db.Column(db.String(200))
    partner_logo_2 = db.Column(db.String(200))
    partner_logo_3 = db.Column(db.String(200))
    partner_logo_4 = db.Column(db.String(200))
    bottom_banner_filename = db.Column(db.String(200)) # Replaces the 4 partner logos
    scanning_active = db.Column(db.Boolean, default=False) # Master toggle for QR scanning
    registration_active = db.Column(db.Boolean, default=True) # Open/Close Registration
    visitors = db.relationship('Visitor', backref='event', lazy=True)

    partners_heading = db.Column(db.String(255), nullable=True)
    partners_body = db.Column(db.Text, nullable=True)

class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    organization = db.Column(db.String(150))
    # organization_address = db.Column(db.String(300)) # Removed
    designation = db.Column(db.String(150))
    # country = db.Column(db.String(100)) # Removed
    status = db.Column(db.String(50), default='Pending') # Pending, Approved, Rejected, Rejected (Capacity), Rejected (Data)
    qr_code_token = db.Column(db.String(100), unique=True)
    invited_by = db.Column(db.String(150)) # "Name of who invited you"
    arrived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
