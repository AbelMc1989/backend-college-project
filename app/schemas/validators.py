import re
from decimal import Decimal, InvalidOperation
from flask import request
from app.utils.exceptions import ValidationError

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
SLUG_REGEX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def get_json_body() -> dict:
    """Безопасно извлекает JSON-объект из тела HTTP-запроса."""
    if not request.is_json:
        raise ValidationError("Заголовок Content-Type должен быть application/json")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Тело запроса должно содержать валидный JSON-объект")
    return data


def require_str(data: dict, field: str, min_len: int = 1, max_len: int = 255) -> str:
    """Валидирует обязательное строковое поле."""
    val = data.get(field)
    if not isinstance(val, str):
        raise ValidationError(f"Поле '{field}' обязательно и должно быть строкой")
    val = val.strip()
    if len(val) < min_len or len(val) > max_len:
        raise ValidationError(f"Длина поля '{field}' должна быть от {min_len} до {max_len} символов")
    return val


def optional_str(data: dict, field: str, max_len: int = 2000) -> str | None:
    """Валидирует необязательное строковое поле."""
    val = data.get(field)
    if val is None:
        return None
    if not isinstance(val, str):
        raise ValidationError(f"Поле '{field}' должно быть строкой")
    val = val.strip()
    if len(val) > max_len:
        raise ValidationError(f"Длина поля '{field}' не может превышать {max_len} символов")
    return val


def require_email(data: dict, field: str = "email") -> str:
    """Проверяет корректность формата электронной почты."""
    email = require_str(data, field, min_len=5, max_len=255).lower()
    if not EMAIL_REGEX.match(email):
        raise ValidationError("Некорректный формат email-адреса")
    return email


def require_slug(data: dict, field: str = "slug") -> str:
    """Проверяет корректность URL-слага (только латиница в нижнем регистре, цифры и дефисы)."""
    slug = require_str(data, field, min_len=2, max_len=140).lower()
    if not SLUG_REGEX.match(slug):
        raise ValidationError(
            f"Поле '{field}' может содержать только строчные латинские буквы, цифры и дефисы"
        )
    return slug


def require_int(data: dict, field: str, min_val: int | None = None, max_val: int | None = None) -> int:
    """Валидирует обязательное целочисленное поле (с защитой от передачи bool, т.к. в Python isinstance(True, int) == True)."""
    val = data.get(field)
    if isinstance(val, bool) or not isinstance(val, int):
        raise ValidationError(f"Поле '{field}' обязательно и должно быть целым числом")
    if min_val is not None and val < min_val:
        raise ValidationError(f"Значение поля '{field}' не может быть меньше {min_val}")
    if max_val is not None and val > max_val:
        raise ValidationError(f"Значение поля '{field}' не может быть больше {max_val}")
    return val


def require_decimal(data: dict, field: str, min_val: Decimal = Decimal("0.00")) -> Decimal:
    """Валидирует денежное значение и приводит его к типу Decimal с точностью до 2 знаков."""
    val = data.get(field)
    if isinstance(val, bool) or val is None or not isinstance(val, (int, float, str)):
        raise ValidationError(f"Поле '{field}' обязательно и должно быть числом")
    try:
        dec = Decimal(str(val)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"Некорректный числовой формат поля '{field}'")
    if dec < min_val:
        raise ValidationError(f"Значение поля '{field}' не может быть меньше {min_val}")
    if dec > Decimal("99999999.99"):
        raise ValidationError(f"Значение поля '{field}' превышает допустимый предел")
    return dec
