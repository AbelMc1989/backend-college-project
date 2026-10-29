from flask import Blueprint, g
from app.schemas.validators import get_json_body, require_email, require_str
from app.services.auth_service import AuthService
from app.utils.responses import success_response
from app.utils.security import jwt_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@auth_bp.post("/register")
def register():
    """Регистрация нового покупателя."""
    data = get_json_body()
    email = require_email(data, "email")
    password = require_str(data, "password", min_len=8, max_len=128)
    full_name = require_str(data, "full_name", min_len=2, max_len=150)

    user, token = AuthService.register_user(email=email, password=password, full_name=full_name)
    return success_response(
        data={"user": user.to_dict(), "access_token": token},
        message="Регистрация успешно завершена",
        status_code=201,
    )


@auth_bp.post("/login")
def login():
    """Аутентификация пользователя и получение JWT-токена."""
    data = get_json_body()
    email = require_email(data, "email")
    password = require_str(data, "password", min_len=1, max_len=128)

    user, token = AuthService.authenticate_user(email=email, password=password)
    return success_response(
        data={"user": user.to_dict(), "access_token": token},
        message="Вход выполнен успешно",
    )


@auth_bp.get("/me")
@jwt_required
def get_current_profile():
    """Получение профиля текущего авторизованного пользователя."""
    return success_response(data=g.current_user.to_dict())
