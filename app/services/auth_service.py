from sqlalchemy import select
from app.extensions import db
from app.models.user import User, UserRole
from app.utils.exceptions import ConflictError, AuthenticationError, AuthorizationError
from app.utils.security import generate_jwt_token


class AuthService:
    """Сервис регистрации и аутентификации пользователей."""

    @staticmethod
    def register_user(email: str, password: str, full_name: str) -> tuple[User, str]:
        """
        Регистрирует нового покупателя (роль customer по умолчанию).
        Возвращает кортеж (User, jwt_token).
        """
        existing = db.session.scalar(select(User).where(User.email == email))
        if existing:
            raise ConflictError("Пользователь с таким email уже зарегистрирован")

        user = User(
            email=email,
            full_name=full_name,
            role=UserRole.CUSTOMER,
            is_active=True,
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        token = generate_jwt_token(user.id, user.role)
        return user, token

    @staticmethod
    def authenticate_user(email: str, password: str) -> tuple[User, str]:
        """
        Проверяет учетные данные пользователя и выдает JWT-токен.
        Использует одинаковое сообщение об ошибке при неверном email или пароле
        для предотвращения перебора учетных записей (User Enumeration).
        """
        user = db.session.scalar(select(User).where(User.email == email))
        if not user or not user.check_password(password):
            raise AuthenticationError("Неверный email или пароль")

        if not user.is_active:
            raise AuthorizationError("Учетная запись заблокирована")

        token = generate_jwt_token(user.id, user.role)
        return user, token
