"""
Application factory for the Axis Solutions Ltd Guest House Booking System.
"""

import os
from flask import Flask, render_template

from config import config_map
from app.extensions import db, login_manager, csrf, mail


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "default")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_map.get(config_name, config_map["default"]))

    # Ensure instance folder exists (for SQLite file)
    os.makedirs(app.instance_path, exist_ok=True)

    # --- Initialize extensions ---------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- Register blueprints -------------------------------------------------
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.employee import employee_bp
    from app.routes.hod import hod_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(hod_bp)
    app.register_blueprint(reports_bp)

    # --- Context processors ---------------------------------------------------
    @app.context_processor
    def inject_globals():
        return {"company_name": app.config.get("COMPANY_NAME", "Axis Solutions Ltd.")}

    # --- Error handlers ---------------------------------------------------
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors.html", code=403,
                                message="You do not have permission to access this page."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors.html", code=404, message="Page not found."), 404

    @app.errorhandler(401)
    def unauthorized(e):
        return render_template("errors.html", code=401, message="Please log in to continue."), 401

    # --- Root redirect -------------------------------------------------------
    from flask import redirect, url_for
    from flask_login import current_user

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin:
                return redirect(url_for("admin.dashboard"))
            if current_user.is_hod:
                return redirect(url_for("hod.dashboard"))
            return redirect(url_for("employee.dashboard"))
        return redirect(url_for("auth.login"))

    return app
