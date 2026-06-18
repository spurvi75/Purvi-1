"""
Configuration for Axis Solutions Ltd - Guest House Booking System.

All sensitive / environment-specific settings are read from environment
variables (or a .env file loaded via python-dotenv). Sensible defaults are
provided for local development with SQLite.

To move to PostgreSQL/MySQL in production, simply set the DATABASE_URL
environment variable, e.g.:

    postgresql://user:password@localhost:5432/axis_guesthouse
    mysql+pymysql://user:password@localhost:3306/axis_guesthouse

No code changes are required - SQLAlchemy will use whichever URL is supplied.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    # --- Core Flask settings -------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    WTF_CSRF_ENABLED = True

    # --- Database --------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "instance", "axis_guesthouse.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Session / security ----------------------------------------------
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set to True when serving over HTTPS in production
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False") == "True"

    # --- Password reset ----------------------------------------------------
    PASSWORD_RESET_EXPIRY_MINUTES = int(os.environ.get("PASSWORD_RESET_EXPIRY_MINUTES", "30"))

    # --- Email / SMTP -------------------------------------------------------
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "False") == "True"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@axisindia.in")
    # When True, emails are printed to console instead of actually sent.
    # Very useful for local development without real SMTP credentials.
    MAIL_SUPPRESS_SEND = os.environ.get("MAIL_SUPPRESS_SEND", "True") == "True"

    # --- Application-specific -----------------------------------------------
    COMPANY_NAME = "Axis Solutions Ltd."
    ADMIN_NOTIFICATION_EMAIL = os.environ.get("ADMIN_NOTIFICATION_EMAIL", "Admin@axisindia.in")
    BOOKING_NUMBER_PREFIX = os.environ.get("BOOKING_NUMBER_PREFIX", "AXIS-GH")
    # Base URL used when building links inside emails (approve / reject / reset)
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5000")

    GRADES = ["A", "B", "C", "D", "E"]
    SINGLE_OCCUPANCY_GRADES = {"A", "B"}
    GENDERS = ["Male", "Female"]


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
