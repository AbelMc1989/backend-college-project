# E-Commerce Backend API (Flask + SQLAlchemy 2.0)

Серверная часть (REST API) интернет-магазина с ролевой моделью доступа (RBAC), атомарным управлением складскими остатками, JWT-аутентификацией и поддержкой SQLite / PostgreSQL.

---

## 1. Требования к окружению

* **Python**: версия 3.10 и выше
* **СУБД**: SQLite 3 (встроена в Python, используется по умолчанию) или PostgreSQL 14+ (при подключении через `DATABASE_URL`)

---

## 2. Пошаговая инструкция по запуску

### Шаг 1. Распаковка архива и переход в директорию проекта
```bash
unzip ecommerce_backend.zip
cd ecommerce_backend
```

### Шаг 2. Создание и активация виртуального окружения
**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Шаг 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### Шаг 4. Настройка переменных окружения
Скопируйте файл `.env.example` в `.env`:
```bash
cp .env.example .env
```
По умолчанию приложение использует локальную базу `sqlite:///ecommerce.db`, которая создается автоматически при первом старте. Для переключения на PostgreSQL укажите строку подключения в `.env`:
```ini
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/ecommerce_db
```

### Шаг 5. Наполнение базы демонстрационными данными (опционально)
Скрипт `seed.py` создаст 3 тестовых аккаунта (Admin, Manager, Customer), категории и стартовый набор товаров:
```bash
python seed.py
```

**Тестовые учетные записи после выполнения `seed.py`:**
| Роль | Email | Пароль | Права доступа |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@store.local` | `AdminPass123!` | Полный доступ + управление пользователями и аналитика |
| **Manager** | `manager@store.local` | `ManagerPass123!` | Управление каталогом, остатками и статусами всех заказов |
| **Customer** | `customer@store.local` | `CustomerPass123!` | Просмотр каталога, управление своей корзиной и заказами |

### Шаг 6. Запуск сервера
```bash
python run.py
```
Сервер запустится по адресу `http://127.0.0.1:5000`.
Проверка работоспособности:
```bash
curl http://127.0.0.1:5000/api/v1/health
```

---

## 3. Запуск автоматических тестов

В проект встроен набор интеграционных тестов (`tests/test_api.py`), проверяющий весь жизненный цикл покупки, списание/возврат остатков и защиту от несанкционированного доступа (RBAC, IDOR):
```bash
pytest -v
```
или через стандартный модуль `unittest`:
```bash
python -m unittest discover -s tests -v
```

---

## 4. Справочник эндпоинтов REST API

Все ответы возвращаются в едином формате JSON (`status: "success"` или `status: "error"`). Для защищенных маршрутов передается заголовок:
`Authorization: Bearer <access_token>`

### Аутентификация (`/api/v1/auth`)
* `POST /api/v1/auth/register` — Регистрация нового покупателя (`email`, `password`, `full_name`).
* `POST /api/v1/auth/login` — Вход в систему и выдача JWT-токена (`email`, `password`).
* `GET /api/v1/auth/me` — Профиль текущего пользователя (`@jwt_required`).

### Каталог и категории (`/api/v1`)
* `GET /api/v1/categories` — Список всех категорий.
* `POST /api/v1/categories` — Создание категории (`manager`, `admin`).
* `PATCH /api/v1/categories/<id>` — Изменение категории (`manager`, `admin`).
* `DELETE /api/v1/categories/<id>` — Удаление пустой категории (`manager`, `admin`).
* `GET /api/v1/products` — Список товаров с фильтрацией и пагинацией. Параметры: `category_id`, `q` (поиск по названию/описанию/SKU), `min_price`, `max_price`, `in_stock=true`, `page`, `per_page`.
* `GET /api/v1/products/<id>` — Детальная карточка товара.
* `POST /api/v1/products` — Создание товара (`manager`, `admin`).
* `PATCH /api/v1/products/<id>` — Обновление цены, описания, активности или остатка `stock` (`manager`, `admin`).

### Корзина (`/api/v1/cart`)
* `GET /api/v1/cart` — Просмотр корзины с подсчетом стоимости (`@jwt_required`).
* `POST /api/v1/cart/items` — Добавление или изменение количества товара (`product_id`, `quantity`). При `quantity: 0` позиция удаляется.
* `DELETE /api/v1/cart/items/<product_id>` — Удаление товара из корзины.
* `DELETE /api/v1/cart` — Полная очистка корзины.

### Заказы (`/api/v1/orders`)
* `POST /api/v1/orders/checkout` — Атомарное оформление заказа из корзины (`shipping_address`, `comment`).
* `GET /api/v1/orders` — Список заказов (покупатель видит свои; менеджер и админ — все, поддерживается фильтр `?status=pending`).
* `GET /api/v1/orders/<id>` — Детали заказа с позициями и историческими ценами.
* `POST /api/v1/orders/<id>/cancel` — Отмена заказа покупателем (только из статуса `pending`, возвращает товары на склад).
* `PATCH /api/v1/orders/<id>/status` — Изменение статуса заказа персоналом (`pending`, `paid`, `shipped`, `completed`, `cancelled`).

### Администрирование (`/api/v1/admin`)
* `GET /api/v1/admin/users` — Список всех пользователей (`admin`).
* `PATCH /api/v1/admin/users/<id>` — Изменение роли (`role`) или блокировка аккаунта (`is_active`) (`admin`).
* `GET /api/v1/admin/stats` — Сводная статистика магазина и подтвержденная выручка (`manager`, `admin`).
