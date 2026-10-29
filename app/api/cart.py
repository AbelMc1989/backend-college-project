from flask import Blueprint, g
from app.schemas.validators import get_json_body, require_int
from app.services.cart_service import CartService
from app.utils.responses import success_response
from app.utils.security import jwt_required

cart_bp = Blueprint("cart", __name__, url_prefix="/api/v1/cart")


@cart_bp.get("")
@jwt_required
def get_cart():
    """Просмотр текущей корзины авторизованного пользователя."""
    cart_data = CartService.get_user_cart(g.current_user.id)
    return success_response(data=cart_data)


@cart_bp.post("/items")
@jwt_required
def set_item():
    """
    Добавление товара в корзину или изменение его количества.
    При передаче quantity = 0 товар удаляется из корзины.
    """
    data = get_json_body()
    product_id = require_int(data, "product_id", min_val=1)
    quantity = require_int(data, "quantity", min_val=0, max_val=1000)

    cart_data = CartService.set_cart_item(
        user_id=g.current_user.id,
        product_id=product_id,
        quantity=quantity,
    )
    return success_response(data=cart_data, message="Корзина обновлена")


@cart_bp.delete("/items/<int:product_id>")
@jwt_required
def remove_item(product_id: int):
    """Удаление позиции товара из корзины."""
    cart_data = CartService.remove_cart_item(
        user_id=g.current_user.id,
        product_id=product_id,
    )
    return success_response(data=cart_data, message="Товар удален из корзины")


@cart_bp.delete("")
@jwt_required
def clear_cart():
    """Полная очистка корзины пользователя."""
    CartService.clear_cart(g.current_user.id)
    return success_response(
        data={"items": [], "total_quantity": 0, "total_amount": 0.0},
        message="Корзина очищена",
    )
