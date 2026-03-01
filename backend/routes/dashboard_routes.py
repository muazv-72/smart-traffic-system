import uuid
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request, session

from backend.auth.decorators import login_required
from backend.database import Hub, User, UserAssignment, UserLog, db
from backend.state import LIVE_TRAFFIC_DATA, USERS_ONLINE

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    current_role = session.get("role", "viewer")
    current_username = session.get("username")
    all_hubs = Hub.query.all()
    # Sort Hubs by Traffic Volume
    hubs_sorted = sorted(
        [(h.id, h) for h in all_hubs], key=lambda x: x[1].traffic, reverse=True
    )

    my_users = []
    all_managers = User.query.filter_by(role="manager").all()

    # Role-Based User Viewing Logic
    if current_role == "admin":
        db_users = User.query.filter_by(role="manager").all()
    elif current_role == "manager":
        assignments = UserAssignment.query.filter_by(
            manager_username=current_username
        ).all()
        assigned_user_names = [a.user_username for a in assignments]
        db_users = (
            User.query.filter(User.username.in_(assigned_user_names)).all()
            if assigned_user_names
            else []
        )
    else:
        db_users = []

    for u in db_users:
        if u.username == current_username:
            continue
        status_text = "Online" if u.username in USERS_ONLINE else "Offline"
        my_users.append({"username": u.username, "duration": status_text})

    return render_template(
        "dashboard.html",
        hubs=hubs_sorted,
        my_users=my_users,
        role=current_role,
        managers=all_managers,
    )


@dashboard_bp.route("/add_hub", methods=["POST"])
@login_required
def add_hub():
    data = request.json
    new_id = f"hub_{uuid.uuid4().hex[:6]}"
    new_hub = Hub(id=new_id, name=data.get("name"), traffic=0)
    db.session.add(new_hub)
    db.session.commit()
    return jsonify({"success": True})


@dashboard_bp.route("/delete_hub", methods=["POST"])
@login_required
def delete_hub():
    hub = Hub.query.get(request.json.get("id"))
    if hub:
        db.session.delete(hub)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404


@dashboard_bp.route("/create_user", methods=["POST"])
@login_required
def create_user():
    data = request.json
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "User exists"}), 400

    new_user = User(
        username=data["username"],
        password=data["password"],
        role=data["role"],
        created_by=session.get("username"),
    )
    db.session.add(new_user)
    db.session.commit()

    # Assign User to Manager if applicable
    if data["role"] == "user":
        mgr = (
            data.get("assigned_manager")
            if session["role"] == "admin"
            else session.get("username")
        )
        if mgr:
            db.session.add(
                UserAssignment(
                    manager_username=mgr, user_username=data["username"]
                )
            )
            db.session.commit()

    return jsonify({"success": True})


@dashboard_bp.route("/change_password", methods=["POST"])
@login_required
def change_password():
    data = request.json
    user = User.query.filter_by(username=session.get("username")).first()
    if user and user.password == data.get("old_password"):
        user.password = data.get("new_password")
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": "Incorrect password"}), 400


@dashboard_bp.route("/user/<username>")
@login_required
def user_profile(username):
    current_role = session.get("role")
    current_username = session.get("username")

    # USER can only see themselves
    if current_role == "user":
        if current_username != username:
            return "Unauthorized", 403

    # MANAGER can only see assigned users
    elif current_role == "manager":
        assignment = UserAssignment.query.filter_by(
            manager_username=current_username, user_username=username
        ).first()

        if not assignment:
            return "Unauthorized", 403

    # ADMIN can see anyone (no restriction)

    target_user = User.query.filter_by(username=username).first()
    logs = (
        UserLog.query.filter_by(username=username)
        .order_by(UserLog.login_time.desc())
        .limit(10)
        .all()
    )

    dates = []
    durations = []

    for log in logs:
        if log.logout_time:
            diff = log.logout_time - log.login_time
        else:
            diff = datetime.utcnow() - log.login_time

        total_seconds = int(diff.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        # For chart (decimal hours)
        durations.append(total_seconds / 3600)

        # For x-axis
        dates.append(log.login_time.strftime("%d-%b"))

        # For table display
        log.formatted_duration = f"{hours}h {minutes}m"

    return render_template(
        "user_profile.html",
        user=target_user,
        logs=logs,
        chart_dates=dates[::-1],
        chart_hours=durations[::-1],
    )


@dashboard_bp.route("/admin_reset_password", methods=["POST"])
@login_required
def admin_reset_password():
    if session["role"] != "admin":
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    target_user = User.query.filter_by(username=data["username"]).first()
    if target_user:
        target_user.password = data["new_password"]
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": "User not found"}), 404


@dashboard_bp.route("/api/hub-traffic")
def get_hub_traffic():
    hubs = Hub.query.all()
    data = []

    for hub in hubs:
        total_traffic = 0

        for cam in hub.cameras:
            total_traffic += LIVE_TRAFFIC_DATA.get(cam.id, {}).get(
                "vehicles", 0
            )

        data.append({"hub_id": hub.id, "traffic": total_traffic})

    return jsonify(data)


@dashboard_bp.route("/analysis/<hub_id>")
def analysis_page(hub_id):

    hub = Hub.query.get_or_404(hub_id)

    lanes = []
    cumulative = {}

    for cam in hub.cameras:

        lane_name = cam.name
        lanes.append(lane_name)

        vehicles = LIVE_TRAFFIC_DATA.get(cam.id, {})

        cumulative[lane_name] = {
            "cars": vehicles.get("cars", 0),
            "buses": vehicles.get("buses", 0),
            "trucks": vehicles.get("trucks", 0),
            "motorcycles": vehicles.get("motorcycles", 0),
            "ambulances": vehicles.get("ambulances", 0),
        }

    return render_template(
        "analysis.html", hub=hub, lanes=lanes, cumulative=cumulative
    )
