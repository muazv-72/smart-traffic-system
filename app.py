from flask import Flask, render_template, request, redirect, session, url_for
import os
from backend.routes.dashboard_routes import dashboard_bp
from backend.routes.analysis_routes import analysis_bp
from backend.routes.camera_routes import camera_bp, start_background_thread
from backend.database import db, User, UserLog
from backend.state import USERS_ONLINE
from datetime import datetime

# Initialize Flask App
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.urandom(24) # Security key for sessions
app.config['SESSION_PERMANENT'] = False

# --- DATABASE CONFIGURATION ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///traffic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app) # Initialize Database

# Prevent browser caching (Ensures live updates work instantly)
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

# Register Blueprints (Connects the route files)
app.register_blueprint(dashboard_bp)
app.register_blueprint(camera_bp)
app.register_blueprint(analysis_bp)
# --- SETUP: CREATE TABLES & ADMIN ---
with app.app_context():
    db.create_all()
    # Auto-create Admin if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password='admin123', role='admin')
        db.session.add(admin)
        db.session.commit()
        print("✅ Database created and Admin user added!")

# --- AUTHENTICATION ROUTES ---
@app.route("/", methods=["GET"])
def root():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return redirect(url_for("dashboard.dashboard"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        # NOTE: For production, use password hashing here!
        if user and user.password == password:
            session.clear()
            session["logged_in"] = True
            session["username"] = user.username
            session["role"] = user.role
            
            USERS_ONLINE.add(user.username)

            # Audit Log: Record Login Time
            new_log = UserLog(username=user.username, login_time=datetime.now())
            db.session.add(new_log)
            db.session.commit()

            return redirect(url_for("dashboard.dashboard"))
        else:
            return render_template("login.html",error="Invalid Credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    username = session.get("username")
    
    # Audit Log: Record Logout Time
    if username:
        last_log = UserLog.query.filter_by(username=username, logout_time=None).order_by(UserLog.id.desc()).first()
        if last_log:
            last_log.logout_time = datetime.now()
            db.session.commit()

    USERS_ONLINE.discard(username)
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    # START THE AI BACKGROUND THREAD
    start_background_thread(app)
    
    # Run the Web Server
    app.run(debug=True, use_reloader=False)