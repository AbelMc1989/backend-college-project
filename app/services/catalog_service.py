from decimal import Decimal
from sqlalchemy import select, or_, func
from app.extensions import db
from app.models.catalog import Category, Product
from app.utils.exceptions import NotFoundError, ConflictError


class CatalogService:
    """Сервис управления категориями, товарами и складскими остатками."""

    # --- Категории ---

    @staticmethod
    def list_categories() -> list[Category]:
        stmt = select(Category).order_by(Category.name.asc())
        return list(db.session.scalars(stmt).all())

    @staticmethod
    def create_category(name: str, slug: str, description: str | None = None) -> Category:
        existing = db.session.scalar(
            select(Category).where(or_(Category.name == name, Category.slug == slug))
        )
        if existing:
            raise ConflictError("Категория с таким названием или slug уже существует")

        category = Category(name=name, slug=slug, description=description)
        db.session.add(category)
        db.session.commit()
        return category

    @staticmethod
    def update_category(category_id: int, data: dict) -> Category:
        category = db.session.get(Category, category_id)
        if not category:
            raise NotFoundError(f"Категория с ID {category_id} не найдена")

        if "name" in data and data["name"] != category.name:
            dup = db.session.scalar(select(Category).where(Category.name == data["name"]))
            if dup:
                raise ConflictError("Категория с таким названием уже существует")
            category.name = data["name"]

        if "slug" in data and data["slug"] != category.slug:
            dup = db.session.scalar(select(Category).where(Category.slug == data["slug"]))
            if dup:
                raise ConflictError("Категория с таким slug уже существует")
            category.slug = data["slug"]

        if "description" in data:
            category.description = data["description"]

        db.session.commit()
        return category

    @staticmethod
    def delete_category(category_id: int) -> None:
        category = db.session.get(Category, category_id)
        if not category:
            raise NotFoundError(f"Категория с ID {category_id} не найдена")

        products_count = db.session.scalar(
            select(func.count(Product.id)).where(Product.category_id == category_id)
        )
        if products_count and products_count > 0:
            raise ConflictError("Невозможно удалить категорию, к которой привязаны товары")

        db.session.delete(category)
        db.session.commit()

    # --- Товары ---

    @staticmethod
    def list_products(
        category_id: int | None = None,
        search_query: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        in_stock_only: bool = False,
        include_inactive: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Product], int]:
        """
        Возвращает отфильтрованный список товаров с пагинацией и общее количество совпадений.
        """
        stmt = select(Product)

        if not include_inactive:
            stmt = stmt.where(Product.is_active.is_(True))
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if search_query:
            pattern = f"%{search_query.strip()}%"
            stmt = stmt.where(
                or_(Product.name.ilike(pattern), Product.description.ilike(pattern), Product.sku.ilike(pattern))
            )
        if min_price is not None:
            stmt = stmt.where(Product.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Product.price <= max_price)
        if in_stock_only:
            stmt = stmt.where(Product.stock > 0)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.session.scalar(count_stmt) or 0

        stmt = stmt.order_by(Product.id.desc()).offset((page - 1) * per_page).limit(per_page)
        items = list(db.session.scalars(stmt).all())
        return items, total

    @staticmethod
    def get_product(product_id: int, include_inactive: bool = False) -> Product:
        product = db.session.get(Product, product_id)
        if not product or (not include_inactive and not product.is_active):
            raise NotFoundError(f"Товар с ID {product_id} не найден")
        return product

    @staticmethod
    def create_product(
        category_id: int,
        sku: str,
        name: str,
        description: str | None,
        price: Decimal,
        stock: int,
        is_active: bool = True,
    ) -> Product:
        category = db.session.get(Category, category_id)
        if not category:
            raise NotFoundError(f"Категория с ID {category_id} не найдена")

        existing_sku = db.session.scalar(select(Product).where(Product.sku == sku))
        if existing_sku:
            raise ConflictError(f"Товар с артикулом (SKU) '{sku}' уже существует")

        product = Product(
            category_id=category_id,
            sku=sku,
            name=name,
            description=description,
            price=price,
            stock=stock,
            is_active=is_active,
        )
        db.session.add(product)
        db.session.commit()
        return product

    @staticmethod
    def update_product(product_id: int, fields: dict) -> Product:
        product = db.session.get(Product, product_id)
        if not product:
            raise NotFoundError(f"Товар с ID {product_id} не найден")

        if "category_id" in fields:
            cat = db.session.get(Category, fields["category_id"])
            if not cat:
                raise NotFoundError(f"Категория с ID {fields['category_id']} не найдена")
            product.category_id = fields["category_id"]

        if "sku" in fields and fields["sku"] != product.sku:
            dup = db.session.scalar(select(Product).where(Product.sku == fields["sku"]))
            if dup:
                raise ConflictError(f"Товар с артикулом '{fields['sku']}' уже существует")
            product.sku = fields["sku"]

        for attr in ("name", "description", "price", "stock", "is_active"):
            if attr in fields:
                setattr(product, attr, fields[attr])

        db.session.commit()
        return product
