from flask import Blueprint, request, g
from app.models.user import UserRole
from app.schemas.validators import get_json_body, require_str, optional_str
from app.services.order_service import OrderService
from app.utils.responses import success_response
from app.utils.security import jwt_required, roles_required

orders_bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")


@orders_bp.post("/checkout")
@jwt_required
def checkout():
    """Оформление нового заказа из текущей корзины пользователя."""
    data = get_json_body()
    shipping_address = require_str(data, "shipping_address", min_len=5, max_len=500)
    comment = optional_str(data, "comment", max_len=1000)

    order = OrderService.checkout(
        user_id=g.current_user.id,
        shipping_address=shipping_address,
        comment=comment,
    )
    return success_response(
        data=order.to_dict(include_items=True),
        message="Заказ успешно оформлен",
        status_code=201,
    )


@orders_bp.get("")
@jwt_required
def list_orders():
    """
    Получение списка заказов.
    Для покупателя возвращаются только его собственные заказы.
    Для менеджера и администратора — все заказы системы с возможностью фильтрации по ?status=...
    """
    status_filter = request.args.get("status")
    orders = OrderService.list_orders(current_user=g.current_user, status_filter=status_filter)
    return success_response(data=[o.to_dict(include_items=False) for o in orders])


@orders_bp.get("/<int:order_id>")
@jwt_required
def get_order(order_id: int):
    """Детальный просмотр заказа и его товарных позиций."""
    order = OrderService.get_order_by_id(order_id=order_id, current_user=g.current_user)
    return success_response(data=order.to_dict(include_items=True))


@orders_bp.post("/<int:order_id>/cancel")
@jwt_required
def cancel_order(order_id: int):
    """Отмена заказа покупателем (разрешена только для статуса pending)."""
    order = OrderService.cancel_order_by_customer(order_id=order_id, current_user=g.current_user)
    return success_response(
        data=order.to_dict(include_items=True),
        message="Заказ отменен, зарезервированные товары возвращены на склад",
    )


@orders_bp.patch("/<int:order_id>/status")
@roles_required(UserRole.MANAGER, UserRole.ADMIN)
def change_order_status(order_id: int):
    """Изменение статуса заказа менеджером или администратором."""
    data = get_json_body()
    new_status = require_str(data, "status", min_len=3, max_len=32)

    order = OrderService.update_order_status_by_staff(order_id=order_id, new_status=new_status)
    return success_response(
        data=order.to_dict(include_items=True),
        message=f"Статус заказа изменен на '{new_status}'",
    )
