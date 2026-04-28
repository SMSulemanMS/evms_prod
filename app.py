from flask import Flask, render_template
from config import Config
from extensions import db, login_manager
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # SQLite Optimization for Azure Files (Crucial for Locking Issues)
    from sqlalchemy import event, Engine
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=DELETE") # Disable WAL for Azure Files compatibility
        cursor.execute("PRAGMA busy_timeout=30000")  # Wait up to 30s instead of failing immediately
        cursor.execute("PRAGMA synchronous=OFF")     # Faster writes, acceptable risk for this app
        cursor.close()

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register Blueprints / Routes
    from routes import main_bp
    # Register Blueprints / Routes
    from routes import main_bp
    app.register_blueprint(main_bp)

    @login_manager.user_loader
    def load_user(user_id):
        from models import Admin
        return Admin.query.get(int(user_id))

    # Create DB context
    with app.app_context():
        db.create_all()
        # Create default admin if not exists
        from models import Admin
        admin_user = Admin.query.filter_by(username='admin').first()
        hardcoded_pass = 'Qds@suhoor737'
        
        if not admin_user:
            # Create if doesn't exist
            default_admin = Admin(username='admin', password=hardcoded_pass) 
            db.session.add(default_admin)
            db.session.commit()
            print("Default admin created.")
        else:
            # Force update if password mismatches (Critical for deployment updates)
            if admin_user.password != hardcoded_pass:
                admin_user.password = hardcoded_pass
                db.session.commit()
                print(f"Admin password updated to match hardcoded value.")

        # --- AUTO-MIGRATION LOGIC ---
        # Ensure new columns exist (location_text, bottom_banner_filename)
        from sqlalchemy import text
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
                    # Boolean in SQLite is usually INTEGER 0/1, but BOOLEAN type works too
                    conn.execute(text("ALTER TABLE event ADD COLUMN scanning_active BOOLEAN DEFAULT 0"))
                    conn.commit()

                if 'registration_active' not in columns:
                    print("MIGRATION: Adding 'registration_active' column to 'event' table...", flush=True)
                    conn.execute(text("ALTER TABLE event ADD COLUMN registration_active BOOLEAN DEFAULT 1"))
                    conn.commit()
        except Exception as e:
            print(f"MIGRATION ERROR: Failed to migrate database: {e}", flush=True)

    return app

app = create_app()

if __name__ == '__main__':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=False)
