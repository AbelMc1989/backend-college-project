from decimal import Decimal, InvalidOperation
from flask import Blueprint, request
from app.models.user import UserRole
from app.schemas.validators import (
    get_json_body,
    require_str,
    optional_str,
    require_slug,
    require_int,
    require_decimal,
)
from app.services.catalog_service import CatalogService
from app.utils.exceptions import ValidationError
from app.utils.responses import success_response
from app.utils.security import roles_required

catalog_bp = Blueprint("catalog", __name__, url_prefix="/api/v1")


# --- Эндпоинты категорий ---

@catalog_bp.get("/categories")
def list_categories():
    """Публичный список всех категорий товаров."""
    categories = CatalogService.list_categories()
    return success_response(data=[c.to_dict() for c in categories])


@catalog_bp.post("/categories")
@roles_required(UserRole.MANAGER, UserRole.ADMIN)
def create_category():
    """Создание новой категории (доступно менеджеру и администратору)."""
    data = get_json_body()
    name = require_str(data, "name", min_len=2, max_len=120)
    slug = require_slug(data, "slug")
    description = optional_str(data, "description", max_len=1000)

    category = CatalogService.create_category(name=name, slug=slug, description=description)
    return success_response(
        data=category.to_dict(),
        message="Категория создана",
        status_code=201,
    )


@catalog_bp.patch("/categories/<int:category_id>")
@roles_required(UserRole.MANAGER, UserRole.ADMIN)
def update_category(category_id: int):
    """Обновление категории (доступно менеджеру и администратору)."""
    data = get_json_body()
    update_fields = {}
    if "name" in data:
        update_fields["name"] = require_str(data, "name", min_len=2, max_len=120)
    if "slug" in data:
        update_fields["slug"] = require_slug(data, "slug")
    if "description" in data:
        update_fields["description"] = optional_str(data, "description", max_len=1000)

    if not update_fields:
        raise ValidationError("Не передано ни одного поля для обновления")

    category = CatalogService.update_category(category_id, update_fields)
    return success_response(data=category.to_dict(), message="Категория обновлена")


@catalog_bp.delete("/categories/<int:category_id>")
@roles_required(UserRole.MANAGER, UserRole.ADMIN)
def delete_category(category_id: int):
    """Удаление пустой категории (доступно менеджеру и администратору)."""
    CatalogService.delete_category(category_id)
    return success_response(message="Категория успешно удалена")


# --- Эндпоинты товаров ---

@catalog_bp.get("/products")
def list_products():
    """
    Публичный каталог товаров с поддержкой фильтрации, поиска и пагинации.
    Query-параметры: category_id, q, min_price, max_price, in_stock, page, per_page.
    """
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except ValueError:
        raise ValidationError("Параметры пагинации page и per_page должны быть целыми числами")

    category_id = request.args.get("category_id")
    if category_id is not None:
        try:
            category_id = int(category_id)
        except ValueError:
            raise ValidationError("Параметр category_id должен быть целым числом")

    min_price = None
    if "min_price" in request.args:
        try:
            min_price = Decimal(request.args["min_price"])
        except InvalidOperation:
            raise ValidationError("Некорректный формат min_price")

    max_price = None
    if "max_price" in request.args:
        try:
            max_price = Decimal(request.args["max_price"])
        except InvalidOperation:
            raise ValidationError("Некорректный формат max_price")

    in_stock_only = request.args.get("in_stock", "false").lower() in ("1", "true", "yes")
    search_query = request.args.get("q")

    products, total = CatalogService.list_products(
        category_id=category_id,
        search_query=search_query,
        min_price=min_price,
        max_price=max_price,
        in_stock_only=in_stock_only,
        include_inactive=False,
        page=page,
        per_page=per_page,
    )

    return success_response(
        data=[p.to_dict() for p in products],
        meta={
            "page": page,
            "per_page": per_page,
            "total_items": total,
            "total_pages": (total + per_page - 1) // per_page if per_page else 1,
        },
    )


@catalog_bp.get("/products/<int:product_id>")
def get_product(product_id: int):
    """Получение детальной карточки товара."""
    product = CatalogService.get_product(product_id, include_inactive=False)
    return success_response(data=product.to_dict())


@catalog_bp.post("/products")
@roles_required(UserRole.MANAGER, UserRole.ADMIN)
def create_product():
    """Добавление нового товара в каталог (доступно менеджеру и администратору)."""
    data = get_json_body()
    category_id = require_int(data, "category_id", min_val=1)
    sku = require_str(data, "sku", min_len=2, max_len=64)
    name = require_str(data, "name", min_len=2, max_len=200)
    description = optional_str(data, "description", max_len=5000)
    price = require_decimal(data, "price", min_val=Decimal("0.01"))
    stock = require_int(data, "stock", min_val=0, max_val=1_000_000)
    is_active = data.get("is_active", True)
    if not isinstance(is_active, bool):
        raise ValidationError("Поле 'is_active' должно иметь булев тип (true/false)")

    product = CatalogService.create_product(
        category_id=category_id,
        sku=sku,
        name=name,
        description=description,
        price=price,
        stock=stock,
        is_active=is_active,
    )
    return success_response(
        data=product.to_dict(),
        message="Товар успешно создан",
        status_code=201,
    )


@catalog_bp.patch("/products/<int:product_id>")
@roles_required(UserRole.MANAGER, UserRole.ADMIN)
def update_product(product_id: int):
    """Обновление параметров товара и его остатков (доступно менеджеру и администратору)."""
    data = get_json_body()
    fields = {}

    if "category_id" in data:
        fields["category_id"] = require_int(data, "category_id", min_val=1)
    if "sku" in data:
        fields["sku"] = require_str(data, "sku", min_len=2, max_len=64)
    if "name" in data:
        fields["name"] = require_str(data, "name", min_len=2, max_len=200)
    if "description" in data:
        fields["description"] = optional_str(data, "description", max_len=5000)
    if "price" in data:
        fields["price"] = require_decimal(data, "price", min_val=Decimal("0.01"))
    if "stock" in data:
        fields["stock"] = require_int(data, "stock", min_val=0, max_val=1_000_000)
    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            raise ValidationError("Поле 'is_active' должно иметь булев тип")
        fields["is_active"] = data["is_active"]

    if not fields:
        raise ValidationError("Не передано ни одного поля для обновления")

    product = CatalogService.update_product(product_id, fields)
    return success_response(data=product.to_dict(), message="Товар успешно обновлен")
