from functools import wraps
from datetime import datetime, timezone, timedelta
import jwt
from flask import request, current_app, g

from app.extensions import db
from app.models.user import User
from app.utils.exceptions import AuthenticationError, AuthorizationError


def generate_jwt_token(user_id: int, role: str) -> str:
    """Генерирует подписанный JWT-токен с идентификатором пользователя и его ролью."""
    now = datetime.now(timezone.utc)
    exp_hours = current_app.config.get("JWT_EXPIRATION_HOURS", 24)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=exp_hours),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def decode_jwt_token(token: str) -> dict:
    """Проверяет подпись и срок действия JWT-токена."""
    try:
        return jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Срок действия токена истек")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Некорректный токен авторизации")


def jwt_required(fn):
    """
    Декоратор для защиты эндпоинтов.
    Проверяет заголовок Authorization: Bearer <token>, загружает пользователя из БД
    и проверяет, что аккаунт активен (защита от использования токенов заблокированных аккаунтов).
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise AuthenticationError("Отсутствует или некорректен заголовок Authorization (ожидается 'Bearer <token>')")

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            raise AuthenticationError("Токен авторизации пуст")

        payload = decode_jwt_token(token)
        try:
            user_id = int(payload["sub"])
        except (KeyError, ValueError):
            raise AuthenticationError("Некорректная структура токена")

        user = db.session.get(User, user_id)
        if not user:
            raise AuthenticationError("Пользователь не найден")
        if not user.is_active:
            raise AuthorizationError("Учетная запись заблокирована администратором")

        # Сохраняем актуальный объект пользователя в контекст запроса Flask
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def roles_required(*allowed_roles: str):
    """
    Декоратор ролевого разграничения доступа (RBAC).
    Разрешает выполнение запроса только пользователям с указанными ролями.
    Используется совместно с или вместо @jwt_required (включает проверку JWT).
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required
        def wrapper(*args, **kwargs):
            user: User = g.current_user
            if user.role not in allowed_roles:
                raise AuthorizationError(
                    f"Недостаточно прав. Требуется одна из ролей: {', '.join(allowed_roles)}"
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator
