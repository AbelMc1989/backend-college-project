from datetime import datetime, timezone
from sqlalchemy import Integer, ForeignKey, DateTime, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class CartItem(db.Model):
    """
    Элемент корзины покупателя.
    Уникальный индекс (user_id, product_id) гарантирует отсутствие дублирующихся строк одного товара.
    """
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_user_product_cart"),
        CheckConstraint("quantity > 0", name="check_cart_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship("User", back_populates="cart_items")
    product = relationship("Product")

    def to_dict(self) -> dict:
        unit_price = float(round(self.product.price, 2)) if self.product else 0.0
        subtotal = round(unit_price * self.quantity, 2)
        return {
            "id": self.id,
            "product_id": self.product_id,
            "sku": self.product.sku if self.product else None,
            "product_name": self.product.name if self.product else None,
            "unit_price": unit_price,
            "quantity": self.quantity,
            "available_stock": self.product.stock if self.product else 0,
            "subtotal": subtotal,
        }
