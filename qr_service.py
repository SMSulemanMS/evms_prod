import qrcode
import os
import uuid
from flask import current_app

def generate_qr_code(data):
    """
    Generates a QR code for the given data, saves it to disk, 
    and returns the filename.
    """
    # Create unique filename
    filename = f"{uuid.uuid4().hex}.png"
    
    # Path to save
    # static/uploads/qr_codes
    save_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qr_codes')
    os.makedirs(save_dir, exist_ok=True)
    
    full_path = os.path.join(save_dir, filename)
    
    # Generate
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(full_path)
    
    return filename
