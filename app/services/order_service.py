from decimal import Decimal
from sqlalchemy import select, delete
from app.extensions import db
from app.models.cart import CartItem
from app.models.catalog import Product
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User, UserRole
from app.utils.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    AuthorizationError,
)


class OrderService:
    """
    Сервис оформления и обработки заказов.
    Обеспечивает транзакционную целостность при списании и возврате складских остатков.
    """

    @staticmethod
    def checkout(user_id: int, shipping_address: str, comment: str | None = None) -> Order:
        """
        Атомарно оформляет заказ на основе текущей корзины покупателя:
        1. Проверяет, что корзина не пуста.
        2. Блокирует и проверяет наличие и активность каждого товара.
        3. Уменьшает складской остаток (stock).
        4. Фиксирует историческую цену и название товара в OrderItem.
        5. Очищает корзину и сохраняет заказ в рамках единой БД-транзакции.
        """
        cart_items = list(
            db.session.scalars(
                select(CartItem).where(CartItem.user_id == user_id).order_by(CartItem.id.asc())
            ).all()
        )
        if not cart_items:
            raise ConflictError("Невозможно оформить заказ: корзина пуста")

        try:
            total_amount = Decimal("0.00")
            order = Order(
                user_id=user_id,
                status=OrderStatus.PENDING,
                total_amount=Decimal("0.00"),
                shipping_address=shipping_address,
                comment=comment,
            )
            db.session.add(order)
            db.session.flush()  # Получаем order.id до коммита

            for c_item in cart_items:
                # Запрашиваем товар с блокировкой строки (при использовании СУБД с поддержкой FOR UPDATE)
                stmt = select(Product).where(Product.id == c_item.product_id).with_for_update()
                product = db.session.scalar(stmt)

                if not product or not product.is_active:
                    raise ConflictError(
                        f"Товар (ID={c_item.product_id}) больше недоступен для покупки"
                    )
                if product.stock < c_item.quantity:
                    raise ConflictError(
                        f"Недостаточно товара '{product.name}' на складе "
                        f"(доступно: {product.stock}, в корзине: {c_item.quantity})"
                    )

                # Списываем остаток со склада
                product.stock -= c_item.quantity

                line_total = (product.price * c_item.quantity).quantize(Decimal("0.01"))
                total_amount += line_total

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name_snapshot=product.name,
                    sku_snapshot=product.sku,
                    unit_price=product.price,
                    quantity=c_item.quantity,
                )
                db.session.add(order_item)

            order.total_amount = total_amount

            # Очищаем корзину пользователя внутри той же транзакции
            db.session.execute(delete(CartItem).where(CartItem.user_id == user_id))
            db.session.commit()
            return order

        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def list_orders(current_user: User, status_filter: str | None = None) -> list[Order]:
        """
        Возвращает список заказов.
        Покупатель видит исключительно свои заказы.
        Менеджер и Администратор видят заказы всех пользователей.
        """
        stmt = select(Order).order_by(Order.created_at.desc(), Order.id.desc())

        if current_user.role == UserRole.CUSTOMER:
            stmt = stmt.where(Order.user_id == current_user.id)

        if status_filter:
            if status_filter not in OrderStatus.ALL:
                raise ValidationError(f"Недопустимый фильтр статуса: {status_filter}")
            stmt = stmt.where(Order.status == status_filter)

        return list(db.session.scalars(stmt).all())

    @staticmethod
    def get_order_by_id(order_id: int, current_user: User) -> Order:
        """
        Возвращает детальную информацию о заказе с защитой от IDOR
        (покупатель не может получить доступ к чужому заказу по ID).
        """
        order = db.session.get(Order, order_id)
        if not order:
            raise NotFoundError(f"Заказ с ID {order_id} не найден")

        if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
            raise AuthorizationError("Доступ к чужому заказу запрещен")

        return order

    @staticmethod
    def cancel_order_by_customer(order_id: int, current_user: User) -> Order:
        """
        Позволяет покупателю отменить собственный заказ, если он еще находится в статусе 'pending'.
        При отмене зарезервированные товары возвращаются на склад.
        """
        order = OrderService.get_order_by_id(order_id, current_user)

        if order.status != OrderStatus.PENDING:
            raise ConflictError(
                f"Покупатель может отменить только заказ в статусе '{OrderStatus.PENDING}'. "
                f"Текущий статус: '{order.status}'"
            )

        return OrderService._transition_to_cancelled(order)

    @staticmethod
    def update_order_status_by_staff(order_id: int, new_status: str) -> Order:
        """
        Изменение статуса заказа менеджером или администратором.
        При переводе в 'cancelled' из любого неотмененного статуса остатки возвращаются на склад.
        """
        if new_status not in OrderStatus.ALL:
            raise ValidationError(
                f"Недопустимый статус '{new_status}'. Допустимые: {', '.join(OrderStatus.ALL)}"
            )

        order = db.session.get(Order, order_id)
        if not order:
            raise NotFoundError(f"Заказ с ID {order_id} не найден")

        if order.status == OrderStatus.CANCELLED and new_status != OrderStatus.CANCELLED:
            raise ConflictError("Отмененный заказ не может быть переведен в другой статус")

        if order.status == OrderStatus.COMPLETED and new_status != OrderStatus.COMPLETED:
            raise ConflictError("Завершенный заказ не подлежит изменению статуса")

        if new_status == OrderStatus.CANCELLED and order.status != OrderStatus.CANCELLED:
            return OrderService._transition_to_cancelled(order)

        order.status = new_status
        db.session.commit()
        return order

    @staticmethod
    def _transition_to_cancelled(order: Order) -> Order:
        """Внутренний атомарный метод отмены заказа с возвратом товаров на склад."""
        try:
            for item in order.items:
                product = db.session.get(Product, item.product_id)
                if product:
                    product.stock += item.quantity
            order.status = OrderStatus.CANCELLED
            db.session.commit()
            return order
        except Exception:
            db.session.rollback()
            raise
