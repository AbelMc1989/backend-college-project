import unittest
from app import create_app
from app.extensions import db
from app.models.user import User, UserRole


class EcommerceBackendTestCase(unittest.TestCase):
    """Комплексный набор интеграционных тестов для проверки всех модулей и механизмов безопасности."""

    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Создаем администратора и менеджера для проверки RBAC
        admin = User(email="admin@test.local", full_name="Admin User", role=UserRole.ADMIN)
        admin.set_password("StrongAdmin123")
        manager = User(email="manager@test.local", full_name="Manager User", role=UserRole.MANAGER)
        manager.set_password("StrongManager123")
        db.session.add_all([admin, manager])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _login(self, email: str, password: str) -> str:
        resp = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        self.assertEqual(resp.status_code, 200)
        return resp.get_json()["data"]["access_token"]

    def _auth_header(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def test_full_ecommerce_lifecycle_and_security(self):
        # 1. Регистрация покупателя
        reg_resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "buyer1@test.local",
                "password": "BuyerPassword123",
                "full_name": "Алексей Покупатель",
            },
        )
        self.assertEqual(reg_resp.status_code, 201)
        buyer1_token = reg_resp.get_json()["data"]["access_token"]

        # Регистрация второго покупателя (для проверки защиты от IDOR)
        reg2_resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "buyer2@test.local",
                "password": "BuyerPassword123",
                "full_name": "Второй Покупатель",
            },
        )
        buyer2_token = reg2_resp.get_json()["data"]["access_token"]

        # 2. Попытка покупателя создать категорию -> 403 Forbidden (RBAC)
        forbidden_cat = self.client.post(
            "/api/v1/categories",
            headers=self._auth_header(buyer1_token),
            json={"name": "Электроника", "slug": "electronics"},
        )
        self.assertEqual(forbidden_cat.status_code, 403)

        # 3. Менеджер создает категорию и товар
        manager_token = self._login("manager@test.local", "StrongManager123")
        cat_resp = self.client.post(
            "/api/v1/categories",
            headers=self._auth_header(manager_token),
            json={"name": "Комплектующие", "slug": "hardware", "description": "PC parts"},
        )
        self.assertEqual(cat_resp.status_code, 201)
        category_id = cat_resp.get_json()["data"]["id"]

        prod_resp = self.client.post(
            "/api/v1/products",
            headers=self._auth_header(manager_token),
            json={
                "category_id": category_id,
                "sku": "GPU-4070-SUPER",
                "name": "Видеокарта RTX 4070 Super",
                "description": "12GB GDDR6X",
                "price": "65000.50",
                "stock": 5,
            },
        )
        self.assertEqual(prod_resp.status_code, 201)
        product_id = prod_resp.get_json()["data"]["id"]

        # 4. Покупатель просматривает каталог с фильтрацией
        list_resp = self.client.get("/api/v1/products?q=4070&in_stock=true")
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(len(list_resp.get_json()["data"]), 1)

        # 5. Попытка добавить в корзину больше товара, чем есть на складе (запрос 10 при остатке 5) -> 409 Conflict
        over_cart_resp = self.client.post(
            "/api/v1/cart/items",
            headers=self._auth_header(buyer1_token),
            json={"product_id": product_id, "quantity": 10},
        )
        self.assertEqual(over_cart_resp.status_code, 409)

        # 6. Добавление корректного количества (2 шт.) в корзину
        cart_resp = self.client.post(
            "/api/v1/cart/items",
            headers=self._auth_header(buyer1_token),
            json={"product_id": product_id, "quantity": 2},
        )
        self.assertEqual(cart_resp.status_code, 200)
        self.assertEqual(cart_resp.get_json()["data"]["total_amount"], 130001.0)

        # 7. Оформление заказа (Checkout)
        checkout_resp = self.client.post(
            "/api/v1/orders/checkout",
            headers=self._auth_header(buyer1_token),
            json={"shipping_address": "г. Москва, ул. Строителей, д. 10, кв. 5", "comment": "Домофон 55"},
        )
        self.assertEqual(checkout_resp.status_code, 201)
        order_data = checkout_resp.get_json()["data"]
        order_id = order_data["id"]
        self.assertEqual(order_data["total_amount"], 130001.0)
        self.assertEqual(order_data["status"], "pending")

        # 8. Проверка списания остатка со склада (5 - 2 = 3)
        prod_after = self.client.get(f"/api/v1/products/{product_id}").get_json()["data"]
        self.assertEqual(prod_after["stock"], 3)

        # 9. Проверка сохранения исторической цены: менеджер меняет цену товара, но в созданном заказе она не меняется
        self.client.patch(
            f"/api/v1/products/{product_id}",
            headers=self._auth_header(manager_token),
            json={"price": "79999.00"},
        )
        order_check = self.client.get(
            f"/api/v1/orders/{order_id}",
            headers=self._auth_header(buyer1_token),
        ).get_json()["data"]
        self.assertEqual(order_check["total_amount"], 130001.0)

        # 10. Проверка защиты от IDOR: Второй покупатель пытается прочитать или отменить чужой заказ -> 403 Forbidden
        idor_get = self.client.get(
            f"/api/v1/orders/{order_id}",
            headers=self._auth_header(buyer2_token),
        )
        self.assertEqual(idor_get.status_code, 403)

        idor_cancel = self.client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers=self._auth_header(buyer2_token),
        )
        self.assertEqual(idor_cancel.status_code, 403)

        # 11. Первый покупатель отменяет свой заказ в статусе pending -> остатки возвращаются на склад (3 + 2 = 5)
        cancel_resp = self.client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers=self._auth_header(buyer1_token),
        )
        self.assertEqual(cancel_resp.status_code, 200)
        self.assertEqual(cancel_resp.get_json()["data"]["status"], "cancelled")

        prod_restored = self.client.get(f"/api/v1/products/{product_id}").get_json()["data"]
        self.assertEqual(prod_restored["stock"], 5)

        # 12. Проверка админ-панели и статистики
        admin_token = self._login("admin@test.local", "StrongAdmin123")
        stats_resp = self.client.get("/api/v1/admin/stats", headers=self._auth_header(admin_token))
        self.assertEqual(stats_resp.status_code, 200)
        stats = stats_resp.get_json()["data"]
        self.assertEqual(stats["products_count"], 1)
        self.assertEqual(stats["orders_total"], 1)


if __name__ == "__main__":
    unittest.main()
