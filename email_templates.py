from flask import render_template
from datetime import datetime

def get_current_year():
    return datetime.now().year

def render_generic_email(full_name, event_title, paragraphs, show_details=False, top_banner_url=None, **kwargs):
    """Helper to render the generic message template."""
    return render_template(
        'email/generic_message.html',
        full_name=full_name,
        event_title=event_title,
        message_paragraphs=paragraphs,
        show_event_details=show_details,
        current_year=get_current_year(),
        top_banner_url=top_banner_url,
        **kwargs
    )

def walkin_welcome_email(full_name, event_title, top_banner_url=None):
    paragraphs = [
        f"Welcome to <strong>{event_title}</strong>!",
        "Thank you for joining us today. We are delighted to have you with us.",
        "We hope you enjoy the event and have a wonderful time."
    ]
    return render_generic_email(full_name, event_title, paragraphs, top_banner_url=top_banner_url)

def registration_acknowledgement_email(full_name, event_title, top_banner_url=None):
    paragraphs = [
        f"Thank you for registering for the <strong>{event_title}</strong>.",
        "We’re delighted by your interest and truly appreciate you taking the time to join us.",
        "We’re pleased to confirm that your registration has been successfully received. In the coming days, you will receive your official confirmation pass, including all event details, to ensure a smooth and seamless entry and a comfortable experience with us.",
        "Thank you once again for your interest and understanding. We look forward to welcoming you.",
        "Warm regards,<br>QDS Team"
    ]
    return render_generic_email(full_name, event_title, paragraphs, top_banner_url=top_banner_url)

def approval_email(full_name, event_title, qr_code_url, event_date, location_url, location_text=None, top_banner_url=None):
    """
    Renders the approval email with QR code.
    Requires: full_name, event_title, qr_code_url, event_date, location_url
    Optional: location_text (will fallback or be empty if not provided)
    """
    return render_template(
        'email/approval.html',
        full_name=full_name,
        event_title=event_title,
        qr_code_url=qr_code_url,
        event_date=event_date,
        location_url=location_url,
        location_text=location_text,
        show_event_details=True,
        current_year=get_current_year(),
        top_banner_url=top_banner_url
    )

def rejection_email(full_name, event_title, top_banner_url=None):
    paragraphs = [
        f"Thank you for your interest in the <strong>{event_title}</strong> and for taking the time to register.",
        "Due to <strong>full capacity</strong>, we regret to inform you that we are unable to confirm your attendance for this gathering.",
        "We truly appreciate your understanding and would be more than happy to invite you to our upcoming events and future gatherings.",
        "Thank you once again for your interest in QDS."
    ]
    return render_generic_email(full_name, event_title, paragraphs, top_banner_url=top_banner_url)

def data_rejection_email(full_name, event_title, registration_url=None, top_banner_url=None):
    paragraphs = [
        f"Thank you for registering for the <strong>{event_title}</strong>.",
        "We have reviewed your registration details and noticed that some information provided (such as phone number or organization details) appears to be <strong>incomplete or incorrect</strong>.",
        "Unfortunately, we are unable to process your registration with the current details.",
        "Kindly <strong>register again</strong> with the correct information.",
        "If you believe this is a mistake, please reply to this email for assistance."
    ]
    
    if registration_url:
        paragraphs.insert(4, f'<div style="margin-top: 15px; margin-bottom: 15px;"><a href="{registration_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Click here to Register Again</a></div>')
        
    return render_generic_email(full_name, event_title, paragraphs, top_banner_url=top_banner_url)

def get_email_style():
    """Deprecated: Styles are now in base_email.html"""
    return ""

