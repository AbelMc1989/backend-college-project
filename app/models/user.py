from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class UserRole:
    """Допустимые системные роли пользователей."""
    CUSTOMER = "customer"  # Покупатель: просмотр каталога, корзина, свои заказы
    MANAGER = "manager"    # Менеджер: управление товарами, категориями, обработка всех заказов
    ADMIN = "admin"        # Администратор: все права менеджера + управление пользователями и аналитика

    ALL = (CUSTOMER, MANAGER, ADMIN)


class User(db.Model):
    """Модель пользователя системы."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default=UserRole.CUSTOMER, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Связи
    cart_items = relationship("CartItem", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", lazy="dynamic")

    def set_password(self, raw_password: str) -> None:
        """Хеширует пароль криптостойким алгоритмом (scrypt/pbkdf2 через Werkzeug)."""
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Проверяет соответствие введенного пароля сохраненному хешу."""
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self) -> dict:
        """Сериализация объекта пользователя без чувствительных полей (password_hash исключен)."""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }
