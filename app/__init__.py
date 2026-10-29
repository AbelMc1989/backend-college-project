import os
from pathlib import Path
from flask import Flask, send_from_directory
from werkzeug.exceptions import HTTPException

from app.config import CONFIG_MAP
from app.extensions import db
from app.utils.exceptions import AppError
from app.utils.responses import error_response, success_response

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def create_app(config_name: str | None = None) -> Flask:
    """
    Фабрика приложения Flask (Application Factory).
    Инициализирует конфигурацию, подключение к БД, модульные Blueprints,
    раздачу клиентского веб-интерфейса, глобальный перехват ошибок и HTTP-заголовки безопасности.
    """
    if not config_name:
        config_name = os.getenv("FLASK_ENV", "development").lower()

    config_cls = CONFIG_MAP.get(config_name, CONFIG_MAP["development"])

    app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="/static")
    app.config.from_object(config_cls)

    # Инициализация ORM
    db.init_app(app)

    # Регистрация модулей (Blueprints)
    from app.api.auth import auth_bp
    from app.api.catalog import catalog_bp
    from app.api.cart import cart_bp
    from app.api.orders import orders_bp
    from app.api.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)

    # Раздача веб-интерфейса для тестирования бэкенда
    @app.get("/")
    def serve_frontend_index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/<path:filename>")
    def serve_frontend_assets(filename: str):
        file_path = FRONTEND_DIR / filename
        if file_path.is_file():
            return send_from_directory(app.static_folder, filename)
        return error_response("NOT_FOUND", "Запрашиваемый ресурс не найден", 404)

    # Служебный эндпоинт проверки работоспособности сервиса (Healthcheck)
    @app.get("/api/v1/health")
    def healthcheck():
        return success_response(data={"service": "ecommerce-backend", "status": "healthy"})

    # Глобальные обработчики исключений (исключают утечку стектрейсов клиенту)
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        return error_response(
            error_code=err.error_code,
            message=err.message,
            status_code=err.status_code,
            details=err.details,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        return error_response(
            error_code=err.name.upper().replace(" ", "_"),
            message=err.description or "HTTP Error",
            status_code=err.code or 500,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_exception(err: Exception):
        app.logger.exception("Unhandled exception occurred: %s", err)
        return error_response(
            error_code="INTERNAL_SERVER_ERROR",
            message="Внутренняя ошибка сервера",
            status_code=500,
        )

    # Установка защитных HTTP-заголовков и поддержка CORS для локальной отладки
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self' http://127.0.0.1:5000 http://localhost:5000; frame-ancestors 'none'"
        )
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        response.headers["Cache-Control"] = "no-store"
        return response

    with app.app_context():
        from app import models as _models  # noqa: F401
        db.create_all()

    return app
