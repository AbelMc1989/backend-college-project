"""
Скрипт первичного наполнения базы данных демонстрационными данными:
создает администратора, менеджера, покупателя, категории и тестовые товары.
Запуск: python seed.py
"""
from decimal import Decimal
from sqlalchemy import select
from app import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.catalog import Category, Product


def seed_database():
    flask_app = create_app()
    with flask_app.app_context():
        # Проверяем, есть ли уже пользователи
        if db.session.scalar(select(User.id).limit(1)) is not None:
            print("[INFO] База данных уже содержит данные. Повторное заполнение пропущено.")
            return

        # 1. Создание учетных записей для каждой роли
        admin = User(
            email="admin@store.local",
            full_name="Системный Администратор",
            role=UserRole.ADMIN,
            is_active=True,
        )
        admin.set_password("AdminPass123!")

        manager = User(
            email="manager@store.local",
            full_name="Менеджер Каталога",
            role=UserRole.MANAGER,
            is_active=True,
        )
        manager.set_password("ManagerPass123!")

        customer = User(
            email="customer@store.local",
            full_name="Иван Покупатель",
            role=UserRole.CUSTOMER,
            is_active=True,
        )
        customer.set_password("CustomerPass123!")

        db.session.add_all([admin, manager, customer])
        db.session.flush()

        # 2. Создание категорий
        cat_hardware = Category(
            name="Комплектующие ПК",
            slug="pc-hardware",
            description="Процессоры, оперативная память, твердотельные накопители и видеокарты",
        )
        cat_peripherals = Category(
            name="Периферия",
            slug="peripherals",
            description="Механические клавиатуры, мыши, мониторы и аудиоинтерфейсы",
        )
        cat_networking = Category(
            name="Сетевое оборудование",
            slug="networking",
            description="Маршрутизаторы, управляемые коммутаторы и точки доступа",
        )
        db.session.add_all([cat_hardware, cat_peripherals, cat_networking])
        db.session.flush()

        # 3. Создание товаров
        products = [
            Product(
                category_id=cat_hardware.id,
                sku="CPU-RYZEN-7700",
                name="Процессор AMD Ryzen 7 7700 OEM",
                description="8 ядер, 16 потоков, базовая частота 3.8 ГГц, сокет AM5",
                price=Decimal("24990.00"),
                stock=15,
                is_active=True,
            ),
            Product(
                category_id=cat_hardware.id,
                sku="SSD-NVME-1TB-KC3000",
                name="NVMe накопитель Kingston KC3000 1024 ГБ",
                description="Интерфейс PCIe 4.0 x4, скорость чтения до 7000 МБ/с",
                price=Decimal("9490.00"),
                stock=30,
                is_active=True,
            ),
            Product(
                category_id=cat_peripherals.id,
                sku="KB-KEYCHRON-K8",
                name="Механическая клавиатура Keychron K8 Pro",
                description="Форм-фактор TKL, поддержка QMK/VIA, переключатели Gateron Brown",
                price=Decimal("10500.00"),
                stock=12,
                is_active=True,
            ),
            Product(
                category_id=cat_networking.id,
                sku="RTR-MIKROTIK-HAP-AX3",
                name="Маршрутизатор MikroTik hAP ax3",
                description="Wi-Fi 6, 4 ядерный процессор ARM 1.8 ГГц, порт 2.5G Ethernet, RouterOS v7",
                price=Decimal("13900.00"),
                stock=8,
                is_active=True,
            ),
        ]
        db.session.add_all(products)
        db.session.commit()

        print("[OK] База данных успешно инициализирована демонстрационными данными.")
        print("Тестовые учетные записи:")
        print("  - Admin:    admin@store.local    / AdminPass123!")
        print("  - Manager:  manager@store.local  / ManagerPass123!")
        print("  - Customer: customer@store.local / CustomerPass123!")


if __name__ == "__main__":
    seed_database()
