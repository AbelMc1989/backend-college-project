from sqlalchemy import select, func
from flask import Blueprint, g
from app.extensions import db
from app.models.user import User, UserRole
from app.models.catalog import Product
from app.models.order import Order, OrderStatus
from app.schemas.validators import get_json_body
from app.utils.exceptions import NotFoundError, ValidationError, ConflictError
from app.utils.responses import success_response
from app.utils.security import roles_required

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


@admin_bp.get("/users")
@roles_required(UserRole.ADMIN)
def list_users():
    """Список всех пользователей системы (только для администратора)."""
    users = list(db.session.scalars(select(User).order_by(User.id.asc())).all())
    return success_response(data=[u.to_dict() for u in users])


@admin_bp.patch("/users/<int:user_id>")
@roles_required(UserRole.ADMIN)
def update_user_role_or_status(user_id: int):
    """
    Изменение роли пользователя или блокировка/разблокировка учетной записи.
    Встроена защита от самоблокировки и лишения прав единственного администратора.
    """
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError(f"Пользователь с ID {user_id} не найден")

    data = get_json_body()
    if "role" not in data and "is_active" not in data:
        raise ValidationError("Укажите поле 'role' и/или 'is_active'")

    if user.id == g.current_user.id:
        if data.get("is_active") is False:
            raise ConflictError("Администратор не может заблокировать собственную учетную запись")
        if "role" in data and data["role"] != UserRole.ADMIN:
            raise ConflictError("Администратор не может понизить собственную роль")

    if "role" in data:
        new_role = data["role"]
        if new_role not in UserRole.ALL:
            raise ValidationError(f"Недопустимая роль. Доступные роли: {', '.join(UserRole.ALL)}")
        user.role = new_role

    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            raise ValidationError("Поле 'is_active' должно быть булевым значением")
        user.is_active = data["is_active"]

    db.session.commit()
    return success_response(data=user.to_dict(), message="Параметры пользователя обновлены")


@admin_bp.get("/stats")
@roles_required(UserRole.ADMIN, UserRole.MANAGER)
def get_store_statistics():
    """Сводная аналитика интернет-магазина по пользователям, каталогу и выручке."""
    total_users = db.session.scalar(select(func.count(User.id))) or 0
    total_products = db.session.scalar(select(func.count(Product.id))) or 0
    out_of_stock_products = db.session.scalar(
        select(func.count(Product.id)).where(Product.stock == 0, Product.is_active.is_(True))
    ) or 0
    total_orders = db.session.scalar(select(func.count(Order.id))) or 0

    revenue_statuses = (OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.COMPLETED)
    total_revenue = db.session.scalar(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.status.in_(revenue_statuses))
    ) or 0

    orders_by_status_rows = db.session.execute(
        select(Order.status, func.count(Order.id)).group_by(Order.status)
    ).all()
    orders_by_status = {status: count for status, count in orders_by_status_rows}

    return success_response(
        data={
            "users_count": total_users,
            "products_count": total_products,
            "out_of_stock_active_products": out_of_stock_products,
            "orders_total": total_orders,
            "orders_by_status": orders_by_status,
            "confirmed_revenue": float(round(total_revenue, 2)),
        }
    )
