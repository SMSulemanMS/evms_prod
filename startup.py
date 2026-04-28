from app import app, db
from sqlalchemy import text
import os
import shutil

# Database Migration Logic for Persistent Storage
def migrate_database():
    with app.app_context():
        try:
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('event')]
            
            with db.engine.connect() as conn:
                if 'location_text' not in columns:
                    print("MIGRATION: Adding 'location_text' column to 'event' table...", flush=True)
                    conn.execute(text("ALTER TABLE event ADD COLUMN location_text TEXT"))
                    conn.commit()
                    
                if 'bottom_banner_filename' not in columns:
                    print("MIGRATION: Adding 'bottom_banner_filename' column to 'event' table...", flush=True)
                    conn.execute(text("ALTER TABLE event ADD COLUMN bottom_banner_filename TEXT"))
                    conn.commit()

                if 'scanning_active' not in columns:
                    print("MIGRATION: Adding 'scanning_active' column to 'event' table...", flush=True)
                    conn.execute(text("ALTER TABLE event ADD COLUMN scanning_active BOOLEAN DEFAULT 0"))
                    conn.commit()

                if 'registration_active' not in columns:
                    print("MIGRATION: Adding 'registration_active' column to 'event' table...", flush=True)
                    conn.execute(text("ALTER TABLE event ADD COLUMN registration_active BOOLEAN DEFAULT 1"))
                    conn.commit()
        except Exception as e:
            print(f"MIGRATION ERROR: Failed to migrate database: {e}", flush=True)

# Ensure persistent storage has necessary static assets
def init_persistent_storage():
    with app.app_context():
        upload_folder = app.config['UPLOAD_FOLDER']
        static_root = os.path.join(app.root_path, 'static')
        
        # Ensure upload folder exists
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        print(f"DEBUG: App Root: {app.root_path}", flush=True)
        print(f"DEBUG: Persistence Target: {upload_folder}", flush=True)

        # Removed asset sync logic as per new strategy:
        # System images (Footer, Partners) are served from static deployment package.
        # Dynamic images (Uploads) are served from Azure File Share via 'serve_upload' route.

# Run initialization
if __name__ == "__main__":
    migrate_database() # Ensure DB schema is up to date
    init_persistent_storage()
    app.run(debug=True)
else:
    # When running via Gunicorn/Azure
    migrate_database() # Ensure DB schema is up to date
    init_persistent_storage()
