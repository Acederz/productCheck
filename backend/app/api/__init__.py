"""API 蓝图注册。"""

from app.api.auth import auth_bp
from app.api.users import users_bp
from app.api.tasks import tasks_bp
from app.api.imports import imports_bp
from app.api.reviews import reviews_bp
from app.api.rules import rules_bp
from app.api.logs import logs_bp
from app.api.export import export_bp
from app.api.approved import approved_bp
from app.api.config import config_bp
from app.api.health import health_bp


def register_blueprints(app):
    """注册所有蓝图。"""
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(tasks_bp, url_prefix="/api/tasks")
    app.register_blueprint(imports_bp, url_prefix="/api/imports")
    app.register_blueprint(reviews_bp, url_prefix="/api/reviews")
    app.register_blueprint(rules_bp, url_prefix="/api/rules")
    app.register_blueprint(logs_bp, url_prefix="/api/logs")
    app.register_blueprint(export_bp, url_prefix="/api/export")
    app.register_blueprint(approved_bp, url_prefix="/api/approved-products")
    app.register_blueprint(config_bp, url_prefix="/api/config")
