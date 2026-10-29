from sqlalchemy import select, delete
from app.extensions import db
from app.models.cart import CartItem
from app.models.catalog import Product
from app.utils.exceptions import NotFoundError, ConflictError


class CartService:
    """Сервис управления корзиной покупателя."""

    @staticmethod
    def get_user_cart(user_id: int) -> dict:
        """Возвращает содержимое корзины пользователя и итоговую стоимость."""
        stmt = select(CartItem).where(CartItem.user_id == user_id).order_by(CartItem.id.asc())
        items = list(db.session.scalars(stmt).all())
        serialized_items = [item.to_dict() for item in items]
        total_amount = round(sum(item["subtotal"] for item in serialized_items), 2)
        total_quantity = sum(item["quantity"] for item in serialized_items)
        return {
            "items": serialized_items,
            "total_quantity": total_quantity,
            "total_amount": total_amount,
        }

    @staticmethod
    def set_cart_item(user_id: int, product_id: int, quantity: int) -> dict:
        """
        Добавляет товар в корзину или обновляет его количество.
        Если передано quantity == 0, позиция удаляется из корзины.
        Проверяет активность товара и достаточность остатка на складе.
        """
        stmt = select(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id
        )
        cart_item = db.session.scalar(stmt)

        if quantity == 0:
            if cart_item:
                db.session.delete(cart_item)
                db.session.commit()
            return CartService.get_user_cart(user_id)

        product = db.session.get(Product, product_id)
        if not product or not product.is_active:
            raise NotFoundError(f"Товар с ID {product_id} не найден или снят с продажи")

        if product.stock < quantity:
            raise ConflictError(
                f"Недостаточно товара '{product.name}' на складе. Доступно: {product.stock}, запрошено: {quantity}"
            )

        if cart_item:
            cart_item.quantity = quantity
        else:
            cart_item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
            db.session.add(cart_item)

        db.session.commit()
        return CartService.get_user_cart(user_id)

    @staticmethod
    def remove_cart_item(user_id: int, product_id: int) -> dict:
        """Удаляет конкретный товар из корзины пользователя."""
        stmt = select(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id
        )
        cart_item = db.session.scalar(stmt)
        if not cart_item:
            raise NotFoundError("Указанный товар отсутствует в вашей корзине")

        db.session.delete(cart_item)
        db.session.commit()
        return CartService.get_user_cart(user_id)

    @staticmethod
    def clear_cart(user_id: int) -> None:
        """Полностью очищает корзину пользователя."""
        db.session.execute(delete(CartItem).where(CartItem.user_id == user_id))
        db.session.commit()
