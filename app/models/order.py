from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Text, Integer, Numeric, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class OrderStatus:
    """Жизненный цикл заказа."""
    PENDING = "pending"        # Создан, товары зарезервированы, ожидает оплаты
    PAID = "paid"              # Оплачен
    SHIPPED = "shipped"        # Отправлен покупателю
    COMPLETED = "completed"    # Доставлен и успешно завершен
    CANCELLED = "cancelled"    # Отменен (остатки товаров возвращены на склад)

    ALL = (PENDING, PAID, SHIPPED, COMPLETED, CANCELLED)


class Order(db.Model):
    """Модель оформленного заказа."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default=OrderStatus.PENDING, nullable=False, index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def to_dict(self, include_items: bool = True) -> dict:
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "user_email": self.user.email if self.user else None,
            "status": self.status,
            "total_amount": float(round(self.total_amount, 2)),
            "shipping_address": self.shipping_address,
            "comment": self.comment,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data


class OrderItem(db.Model):
    """
    Позиция внутри заказа.
    Хранит исторический снимок названия товара (product_name_snapshot) и цены (unit_price)
    на момент оформления заказа, чтобы последующие изменения в каталоге не искажали историю покупок.
    """
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_order_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="check_order_item_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    sku_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")

    def to_dict(self) -> dict:
        unit_p = float(round(self.unit_price, 2))
        return {
            "id": self.id,
            "product_id": self.product_id,
            "sku": self.sku_snapshot,
            "product_name": self.product_name_snapshot,
            "unit_price": unit_p,
            "quantity": self.quantity,
            "subtotal": round(unit_p * self.quantity, 2),
        }
