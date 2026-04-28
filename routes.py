from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import Admin, Event, Visitor
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid
# Services
from email_service import send_email 
from qr_service import generate_qr_code
import email_templates

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('landing.html')

# Custom route to serve uploads from persistent storage with fallback
@main_bp.route('/uploads/<path:filename>')
def serve_upload(filename):
    # 1. Try Persistent Storage
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if os.path.exists(os.path.join(upload_folder, filename)):
        return send_from_directory(upload_folder, filename)
    
    # 2. Try Static Uploads (Fallback for built-in assets)
    # Check 'static/uploads' and root 'static' just in case
    static_uploads = os.path.join(current_app.root_path, 'static', 'uploads')
    if os.path.exists(os.path.join(static_uploads, filename)):
        return send_from_directory(static_uploads, filename)
        
    static_root = os.path.join(current_app.root_path, 'static')
    if os.path.exists(os.path.join(static_root, filename)):
        return send_from_directory(static_root, filename)
        
    # 3. 404 if nowhere
    return "File Not Found", 404

# --- ADMIN ROUTES ---

@main_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Admin.query.filter_by(username=username).first()
        if user and user.password == password: # Plain text check
            login_user(user)
            return redirect(url_for('main.admin_dashboard'))
        else:
            flash('Invalid username or password', 'login_error')
            return redirect(url_for('main.index'))
            
    return render_template('admin/login.html')

@main_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    events = Event.query.all()
    
    # Filter by Event
    selected_event_id = request.args.get('event_id', type=int)
    selected_event = None
    
    if selected_event_id:
        selected_event = Event.query.get(selected_event_id)
    
    # Logic for Insights
    # Default: Aggregated or Most Recent?
    # User said: "accumulated insights like total events... below that drop down to select an event"
    # So we always show Total Events.
    # Then IF selected, show: Invite Sent vs Participated vs Pending
    
    # Initial Aggregate Stats
    total_events = len(events)
    all_visitors = Visitor.query.all()
    
    aggregate_stats = {
        'total_registrations': len(all_visitors),
        'participated': sum(1 for v in all_visitors if v.arrived),
        'online_attended': sum(1 for v in all_visitors if v.arrived and v.status != 'Walk-in'),
        'walkin_attended': sum(1 for v in all_visitors if v.arrived and v.status == 'Walk-in'),
        'pending': sum(1 for v in all_visitors if v.status == 'Pending'),
        'rejected': sum(1 for v in all_visitors if 'Rejected' in v.status)
    }
    
    # Event-Specific Data (or Empty if none selected)
    stats = {
        'total_registrations': 0,
        'participated': 0,
        'online_attended': 0,
        'walkin_attended': 0,
        'pending': 0,
        'rejected': 0
    }
    
    attendees = []
    non_attendees = []
    
    if selected_event:
        visitors = Visitor.query.filter_by(event_id=selected_event.id).all()
        
        stats['total_registrations'] = len(visitors) # "Invite Sent" proxy
        stats['participated'] = sum(1 for v in visitors if v.arrived)
        stats['online_attended'] = sum(1 for v in visitors if v.arrived and v.status != 'Walk-in')
        stats['walkin_attended'] = sum(1 for v in visitors if v.arrived and v.status == 'Walk-in')
        stats['pending'] = sum(1 for v in visitors if v.status == 'Pending')
        stats['rejected'] = sum(1 for v in visitors if 'Rejected' in v.status)
        
        attendees = [v for v in visitors if v.arrived]
        non_attendees = [v for v in visitors if not v.arrived]

    return render_template('admin/dashboard.html', 
                           events=events, 
                           selected_event=selected_event, 
                           total_events=total_events,
                           aggregate_stats=aggregate_stats,
                           stats=stats,
                           attendees=attendees,
                           non_attendees=non_attendees)



@main_bp.route('/admin/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main_bp.route('/admin/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        title = request.form.get('title')
        location_url = request.form.get('location_url')
        location_text = request.form.get('location_text')
        description = request.form.get('description')
        date_str = request.form.get('date_time') # Expects YYYY-MM-DDTHH:MM
        
        # Handle Date
        try:
            date_time = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format')
            return redirect(url_for('main.create_event'))

        # Handle Files
        banner = request.files.get('banner')
        logo = request.files.get('logo')
        bottom_banner = request.files.get('bottom_banner')
        
        banner_filename = None
        logo_filename = None
        bottom_banner_filename = None

        if banner:
            filename = secure_filename(f"banner_{uuid.uuid4().hex}_{banner.filename}")
            banner.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            banner_filename = filename
            
        if logo:
            filename = secure_filename(f"logo_{uuid.uuid4().hex}_{logo.filename}")
            logo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            logo_filename = filename
            
        if bottom_banner:
            filename = secure_filename(f"footer_{uuid.uuid4().hex}_{bottom_banner.filename}")
            bottom_banner.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            bottom_banner_filename = filename

        # Create Event
        # Generate simple slug from title
        url_slug = title.lower().replace(' ', '-') + '-' + uuid.uuid4().hex[:6]

        new_event = Event(
            title=title,
            location_url=location_url,
            location_text=location_text,
            description=description,
            date_time=date_time,
            banner_filename=banner_filename,
            logo_filename=logo_filename,
            bottom_banner_filename=bottom_banner_filename,
            url_slug=url_slug
        )
        
        db.session.add(new_event)
        db.session.commit()
        
        flash(f'Event Created! URL: {request.host_url}event/{url_slug}')
        return redirect(url_for('main.admin_dashboard'))

    return render_template('admin/create_event.html')

@main_bp.route('/admin/event/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        # Accept ONLY the bottom_banner file
        bottom_banner = request.files.get('bottom_banner')
        
        if bottom_banner:
            filename = secure_filename(f"footer_{uuid.uuid4().hex}_{bottom_banner.filename}")
            bottom_banner.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            # Update the event
            event.bottom_banner_filename = filename
            db.session.commit()
            flash(f'Footer banner updated for event: {event.title}')
        else:
            flash('No new file uploaded. Event remains unchanged.', 'info')
            
        return redirect(url_for('main.admin_dashboard'))

    return render_template('admin/edit_event.html', event=event)

@main_bp.route('/admin/event/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    # 1. Delete associated visitors first (Manual Cascade)
    Visitor.query.filter_by(event_id=event_id).delete()
    
    # 2. Delete the event
    db.session.delete(event)
    db.session.commit()
    
    flash(f'Event "{event.title}" has been deleted.')
    return redirect(url_for('main.admin_dashboard'))

@main_bp.route('/admin/event/<int:event_id>/toggle_scanning', methods=['POST'])
@login_required
def toggle_scanning(event_id):
    event = Event.query.get_or_404(event_id)
    # Toggle
    event.scanning_active = not event.scanning_active
    db.session.commit()
    
    status = "Active" if event.scanning_active else "Inactive"
    flash(f'Scanning for "{event.title}" is now {status}.')
    
    # Redirect back to where they came from (Dashboard or Details)
    # For now, Dashboard is the main place
    return redirect(url_for('main.admin_dashboard', event_id=event.id))

@main_bp.route('/admin/event/<int:event_id>/toggle_registration', methods=['POST'])
@login_required
def toggle_registration(event_id):
    event = Event.query.get_or_404(event_id)
    # Toggle
    event.registration_active = not event.registration_active
    db.session.commit()
    
    status = "Open" if event.registration_active else "Closed"
    flash(f'Registration for "{event.title}" is now {status}.')
    
    return redirect(url_for('main.admin_dashboard', event_id=event.id))

@main_bp.route('/admin/event/<int:event_id>/export_visitors')
@login_required
def export_visitors(event_id):
    import csv
    import io
    from flask import Response

    event = Event.query.get_or_404(event_id)
    visitors = Visitor.query.filter_by(event_id=event_id).all()

    # Generate CSV in memory
    def generate():
        data = io.StringIO()
        w = csv.writer(data)

        # Header
        w.writerow(('Full Name', 'Email', 'Phone', 'Organization', 'Designation', 'Status', 'Arrived', 'Invited By', 'Registration Date'))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # Rows
        for v in visitors:
            w.writerow((
                v.full_name,
                v.email,
                v.phone,
                v.organization,
                v.designation,
                v.status,
                "Yes" if v.arrived else "No",
                v.invited_by,
                v.created_at.strftime('%Y-%m-%d %H:%M')
            ))
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    # Use a stream response to avoid loading everything into memory
    response = Response(generate(), mimetype='text/csv')
    filename = f"{event.title.replace(' ', '_')}_Visitors_{datetime.now().strftime('%Y-%m-%d')}.csv"
    response.headers.set('Content-Disposition', 'attachment', filename=filename)
    return response

@main_bp.route('/admin/event/<int:event_id>/visitors')
@login_required
def event_visitors(event_id):
    event = Event.query.get_or_404(event_id)
    visitors = Visitor.query.filter_by(event_id=event_id).all()
    return render_template('admin/event_visitors.html', event=event, visitors=visitors)

@main_bp.route('/admin/visitor/<int:visitor_id>/approve')
@login_required
def approve_visitor(visitor_id):
    visitor = Visitor.query.get_or_404(visitor_id)
    event = visitor.event
    
    
    if visitor.status != 'Pending':
        flash(f'Action Blocked: Visitor {visitor.full_name} has already been processed (Status: {visitor.status}).', 'warning')
        return redirect(url_for('main.event_visitors', event_id=visitor.event_id))

    if visitor.status != 'Approved':
        visitor.status = 'Approved'
        
        # Generate Token
        token = str(uuid.uuid4())
        visitor.qr_code_token = token
        
        # Determine Base URL
        # NOTE: For local testing from a mobile phone, 'localhost' or '127.0.0.1' won't work.
        # Ideally, this should be the LAN IP (e.g., http://192.168.1.5:5000) or a public domain.
        # We will use request.host_url, but if that returns localhost, mobile scan won't react well.
        # For now, we embed the full URL constructed from the current request host.
        scan_url = url_for('main.scan_qr', token=token, _external=True)
        
        # Generate QR Code with the URL
        qr_filename = generate_qr_code(scan_url)
        
        # CID embedding path
        qr_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qr_codes', qr_filename)
        
        # Public URL (just in case)
        qr_url = url_for('main.serve_upload', filename=f'qr_codes/{qr_filename}', _external=True)

        db.session.commit()
        
        # Prepare Banner URL
        top_banner_url = None
        if event.banner_filename:
            top_banner_url = url_for('main.serve_upload', filename=event.banner_filename, _external=True)

        # Send Email
        html_body = email_templates.approval_email(
            visitor.full_name, 
            event.title, 
            qr_url, 
            event.date_time.strftime('%A, %B %d, %Y at %H:%M'), 
            event.location_url,
            location_text=event.location_text,
            top_banner_url=top_banner_url
        )
        # Pass qr_path to be embedded
        send_email(visitor.email, f"Registration Confirmed – Your QR Code Entry Pass | {event.title}", html_body, image_path=qr_path)
        
        flash(f'Visitor {visitor.full_name} approved and email sent.')
    
    return redirect(url_for('main.event_visitors', event_id=visitor.event_id))

@main_bp.route('/api/scan/<token>')
def scan_qr(token):
    visitor = Visitor.query.filter_by(qr_code_token=token).first_or_404()
    
    # CHECK: Is Scanning Active?
    event = visitor.event
    if not event.scanning_active:
         return f"""
        <html>
            <body style="font-family: sans-serif; text-align: center; padding: 50px; background-color: #fff3cd;">
                <h1 style="color: #856404;">Event Not Started</h1>
                <p style="font-size: 18px; color: #856404;">Scanning is currently inactive for <strong>{event.title}</strong>.</p>
                <hr style="border: 1px solid #ffeeba; margin: 20px auto; width: 50%;">
                <p style="color: #333;">Please present this QR code at the <strong>event venue check-in desk</strong> when the event starts.</p>
                <p style="color: #555; font-style: italic;">(Marking attendance is disabled at this time)</p>
            </body>
        </html>
        """

    if not visitor.arrived:
        visitor.arrived = True
        db.session.commit()
        status = "Marked as Arrived"
        color = "green"
    else:
        status = "Already Checked In"
        color = "orange"
        
    # Simple response for the scanner
    return f"""
    <html>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: {color};">{status}</h1>
            <h2>{visitor.full_name}</h2>
            <p>{visitor.designation} at {visitor.organization}</p>
            <p>Email: {visitor.email}</p>
        </body>
    </html>
    """

@main_bp.route('/admin/visitor/<int:visitor_id>/reject/capacity')
@login_required
def reject_visitor_capacity(visitor_id):
    visitor = Visitor.query.get_or_404(visitor_id)
    event = visitor.event
    
    if visitor.status != 'Pending':
        flash(f'Action Blocked: Visitor {visitor.full_name} has already been processed (Status: {visitor.status}).', 'warning')
        return redirect(url_for('main.event_visitors', event_id=visitor.event_id))
    
    if visitor.status != 'Rejected':
        visitor.status = 'Rejected' # or 'Rejected (Capacity)' but simplistic 'Rejected' is fine
        db.session.commit()
        
        # Prepare Banner URL
        top_banner_url = None
        if event.banner_filename:
            top_banner_url = url_for('main.serve_upload', filename=event.banner_filename, _external=True)

        # Send Email #4 (Capacity)
        html_body = email_templates.rejection_email(visitor.full_name, event.title, top_banner_url=top_banner_url)
        send_email(visitor.email, f"Update on Your Registration – {event.title}", html_body)
        
        flash(f'Visitor {visitor.full_name} rejected (Full Capacity).')
    
    return redirect(url_for('main.event_visitors', event_id=visitor.event_id))

@main_bp.route('/admin/visitor/<int:visitor_id>/reject/data')
@login_required
def reject_visitor_data(visitor_id):
    visitor = Visitor.query.get_or_404(visitor_id)
    event = visitor.event
    visitor_name = visitor.full_name
    
    if visitor.status != 'Pending':
        flash(f'Action Blocked: Visitor {visitor_name} has already been processed (Status: {visitor.status}).', 'warning')
        return redirect(url_for('main.event_visitors', event_id=visitor.event_id))
    
    # 1. Prepare Banner URL
    top_banner_url = None
    if event.banner_filename:
        top_banner_url = url_for('main.serve_upload', filename=event.banner_filename, _external=True)

    # 2. Prepare Registration URL
    # Assuming standard registration route
    registration_url = url_for('main.event_registration', url_slug=event.url_slug, _external=True)

    # 3. Send New Email (Wrong Data)
    html_body = email_templates.data_rejection_email(
        visitor_name, 
        event.title, 
        registration_url=registration_url,
        top_banner_url=top_banner_url
    )
    send_email(visitor.email, f"Action Required: Update on Your Registration – {event.title}", html_body)
    
    # 4. DELETE behavior instead of Status Update
    db.session.delete(visitor)
    db.session.commit()
    
    flash(f'Visitor {visitor_name} rejected (Wrong Submission) and record deleted. Email sent.')
    
    return redirect(url_for('main.event_visitors', event_id=visitor.event_id))

@main_bp.route('/admin/visitor/<int:visitor_id>/delete', methods=['POST'])
@login_required
def delete_visitor(visitor_id):
    visitor = Visitor.query.get_or_404(visitor_id)
    event_id = visitor.event_id
    visitor_name = visitor.full_name
    
    db.session.delete(visitor)
    db.session.commit()
    
    flash(f'Submission for {visitor_name} deleted. They can now register again.')
    return redirect(url_for('main.event_visitors', event_id=event_id))


# --- PUBLIC ROUTES ---

@main_bp.route('/event/<url_slug>', methods=['GET', 'POST'])
def event_registration(url_slug):
    event = Event.query.filter_by(url_slug=url_slug).first_or_404()
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        # 1. Validate Work Email
        public_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'live.com', 'icloud.com']
        domain = email.split('@')[-1].lower()
        if domain in public_domains:
            # return "Error: Please use your official work email address. Personal email domains are not accepted."
            return render_template('public/success.html',
                title="Invalid Email Domain",
                message="Please use your official work email address.<br>Personal email domains (gmail, yahoo, etc.) are not accepted.",
                color="#ef4444",
                icon="fas fa-exclamation-circle",
                event=event
            )
        
        # 2. Validate Email Confirmation
        confirm_email = request.form.get('confirm_email')
        if confirm_email and email != confirm_email:
             return render_template('public/success.html',
                title="Email Mismatch",
                message="The email addresses you entered do not match. Please go back and try again.",
                color="#ef4444",
                icon="fas fa-exclamation-circle",
                event=event
            )

        # Check if already registered
        existing = Visitor.query.filter_by(event_id=event.id, email=email).first()
        if existing:
            # return "Your request has already been received. Please contact admin."
            return render_template('public/success.html',
                title="Already Registered",
                message="Your request has already been received.<br>Please contact admin if you need assistance.",
                color="#f59e0b",
                icon="fas fa-info-circle",
                event=event
            )
            
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        if not phone:
            phone = "Not Provided"
        organization = request.form.get('organization')
        designation = request.form.get('designation')
        # organization_address = request.form.get('organization_address') # Removed
        # invited_by = request.form.get('invited_by') # Removed
        # country = request.form.get('country') # Removed
        
        visitor = Visitor(
            event_id=event.id,
            full_name=full_name,
            email=email,
            phone=phone,
            organization=organization,
            designation=designation,
            # organization_address=organization_address, # Removed
            # invited_by=invited_by # Removed
        )
        
        db.session.add(visitor)
        db.session.commit()
        
        # Prepare Banner URL
        top_banner_url = None
        if event.banner_filename:
            top_banner_url = url_for('main.serve_upload', filename=event.banner_filename, _external=True)

        # CHECK: Opens/Closed Registration?
        if not event.registration_active:
             return render_template('public/success.html',
                title="Registration Closed / Full Capacity",
                message="Sorry, we are at full capacity.<br>Please contact QDS marketing department for further details.",
                color="#f59e0b", # Orange
                icon="fas fa-exclamation-triangle",
                event=event
            )

        # Send Acknowledgement Email (ONLY if Open)
        html_body = email_templates.registration_acknowledgement_email(full_name, event.title, top_banner_url=top_banner_url)
        send_email(email, f"Registration Acknowledgement – {event.title}", html_body)
        
        return render_template('public/success.html', event=event)

    return render_template('public/registration.html', event=event)

@main_bp.route('/event/<url_slug>/walkin', methods=['GET', 'POST'])
def walkin_registration(url_slug):
    event = Event.query.filter_by(url_slug=url_slug).first_or_404()
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        # 1. Validate Work Email
        public_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'live.com', 'icloud.com']
        domain = email.split('@')[-1].lower()
        if domain in public_domains:
            return render_template('public/success.html',
                title="Invalid Email Domain",
                message="Please use your official work email address.<br>Personal email domains (gmail, yahoo, etc.) are not accepted.",
                color="#ef4444",
                icon="fas fa-exclamation-circle",
                event=event
            )
        
        # 2. Validate Email Confirmation
        confirm_email = request.form.get('confirm_email')
        if confirm_email and email != confirm_email:
             return render_template('public/success.html',
                title="Email Mismatch",
                message="The email addresses you entered do not match. Please go back and try again.",
                color="#ef4444",
                icon="fas fa-exclamation-circle",
                event=event
            )

        # Check if already registered
        existing = Visitor.query.filter_by(event_id=event.id, email=email).first()
        if existing:
             return render_template('public/success.html',
                title="Already Registered",
                message="You are already registered.",
                color="#f59e0b",
                icon="fas fa-info-circle",
                event=event
            )
            
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        if not phone:
             phone = "Not Provided"
        organization = request.form.get('organization')
        designation = request.form.get('designation')
        # organization_address = request.form.get('organization_address') # Removed
        # invited_by = request.form.get('invited_by') # Removed
        
        visitor = Visitor(
            event_id=event.id,
            full_name=full_name,
            email=email,
            phone=phone,
            organization=organization,
            designation=designation,
            # organization_address=organization_address,
            # invited_by=invited_by,
            arrived=True,          # Walk-ins are physically there
            status='Walk-in'       # Mark as Walk-in/Approved
        )
        
        db.session.add(visitor)
        db.session.commit()
        
        # Prepare Banner URL
        top_banner_url = None
        if event.banner_filename:
            top_banner_url = url_for('main.serve_upload', filename=event.banner_filename, _external=True)

        # Send Welcome Email
        html_body = email_templates.walkin_welcome_email(full_name, event.title, top_banner_url=top_banner_url)
        send_email(email, f"Welcome to {event.title}", html_body)
        
        return render_template('public/success.html',
            title="Welcome!",
            message="Thank you for registering.<br>You may proceed to the event directly.",
            color="#4caf50",
            icon="fas fa-door-open",
            event=event
        )

    # Use the same registration template logic
    return render_template('public/registration.html', event=event)
