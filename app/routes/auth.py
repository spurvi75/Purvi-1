"""
Authentication routes: login, logout, forgot password, reset password,
change password.
"""

from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, PasswordResetToken
from app.forms import LoginForm, ForgotPasswordForm, ResetPasswordForm, ChangePasswordForm
from app.utils.email_utils import send_password_reset_email

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password.", "danger")
        elif not user.is_active_user:
            flash("Your account is deactivated. Please contact Admin.", "danger")
        else:
            login_user(user)
            flash(f"Welcome, {user.name}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        # Always show the same message regardless of whether the email
        # exists, to avoid leaking which emails are registered.
        if user and user.is_active_user:
            reset = PasswordResetToken.generate_for_user(
                user, expiry_minutes=current_app.config["PASSWORD_RESET_EXPIRY_MINUTES"]
            )
            reset_url = url_for("auth.reset_password", token=reset.token, _external=True)
            send_password_reset_email(user, reset_url)
        flash("If the email is registered, a password reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    reset = PasswordResetToken.query.filter_by(token=token).first()
    if reset is None or not reset.is_valid():
        flash("This password reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = reset.user
        user.set_password(form.password.data)
        reset.used = True
        db.session.commit()
        flash("Your password has been reset successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password changed successfully.", "success")
            return redirect(url_for("index"))
    return render_template("auth/change_password.html", form=form)
