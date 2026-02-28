from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# 1. USER TABLE (Login & Roles)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'manager', 'user'
    created_by = db.Column(db.String(50), default="system")
    logs = db.relationship('UserLog', backref="user", cascade="all, delete")

# 2. HUB TABLE (Intersections)
class Hub(db.Model):
    __tablename__ = "hub"
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    traffic = db.Column(db.Integer, default=0)
    cameras = db.relationship('Camera', backref='hub', cascade="all, delete")
    

# 3. CAMERA TABLE (Video Sources)
class Camera(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ip = db.Column(db.String(200), nullable=False) # Video Path
    hub_id = db.Column(db.String(50), db.ForeignKey('hub.id'), nullable=False, index=True)
    light = db.Column(db.Enum("red", "yellow", "green", name="light_status"), default="red") # current status
    vehicles = db.Column(db.Integer, default=0)
    roi = db.Column(db.String(50), nullable=True) # Region of Interest coordinates

# 4. ASSIGNMENT TABLE (Manager -> User)
class UserAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    manager_username = db.Column(db.String(50), db.ForeignKey('user.username'), nullable=False)
    user_username = db.Column(db.String(50), db.ForeignKey('user.username'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.now)

# 5. LOGS TABLE (Audit Trail)
class UserLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), db.ForeignKey('user.username'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.now)
    logout_time = db.Column(db.DateTime, nullable=True)
    
    def duration(self):
        if self.logout_time:
            delta = self.logout_time - self.login_time
            return str(delta).split('.')[0]
        return "Active"