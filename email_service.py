import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from flask import current_app
import os

def send_email(to_email, subject, html_content, image_path=None):
    """
    Sends an email using standard SMTP.
    Supports embedding an image (like a QR code) with Content-ID if image_path is provided.
    """
    smtp_server = current_app.config.get('SMTP_SERVER')
    smtp_port = current_app.config.get('SMTP_PORT', 587)
    smtp_username = current_app.config.get('SMTP_USERNAME')
    smtp_password = current_app.config.get('SMTP_PASSWORD')
    smtp_use_tls = current_app.config.get('SMTP_USE_TLS', 'True').lower() == 'true'
    sender_email = current_app.config.get('SENDER_EMAIL_ADDRESS')

    # MOCK MODE / VALIDATION
    if not smtp_server or not smtp_username:
        print(f"\n[MOCK EMAIL - SMTP NOT CONFIGURED] To: {to_email}")
        print(f"Subject: {subject}")
        # print("Content: (Hidden)\n")
        return True

    try:
        # Create message container: 'related' needed for inline images
        msg = MIMEMultipart('related')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email

        # Create alternative part for HTML
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)

        # Attach HTML content
        part = MIMEText(html_content, 'html')
        msg_alternative.attach(part)

        # Attach Image (QR Code) if provided
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                img_data = f.read()
                
            img = MIMEImage(img_data)
            # Define the Content ID (CID) to match the HTML src="cid:qr_code"
            img.add_header('Content-ID', '<qr_code>')
            img.add_header('Content-Disposition', 'inline', filename=os.path.basename(image_path))
            msg.attach(img)

        # Connect to server
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        
        if smtp_use_tls:
            server.starttls()
            
        # Login
        server.login(smtp_username, smtp_password)
        
        # Send
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        
        print(f"Email sent successfully to {to_email} via SMTP.")
        return True
    
    except Exception as e:
        print(f"\n[SMTP EMAIL FAILED] Error: {e}")
        print(f"[FALLBACK LOG] To: {to_email} | Subject: {subject}\n")
        return False
