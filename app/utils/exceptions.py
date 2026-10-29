class AppError(Exception):
    """Базовое исключение бизнес-логики приложения."""
    status_code = 400
    error_code = "BAD_REQUEST"

    def __init__(self, message: str, status_code: int | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}


class ValidationError(AppError):
    """Ошибка валидации входных данных (HTTP 422)."""
    status_code = 422
    error_code = "VALIDATION_ERROR"


class AuthenticationError(AppError):
    """Ошибка аутентификации пользователя (HTTP 401)."""
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"


class AuthorizationError(AppError):
    """Отказ в доступе из-за недостаточных прав (HTTP 403)."""
    status_code = 403
    error_code = "FORBIDDEN"


class NotFoundError(AppError):
    """Запрашиваемый ресурс не найден (HTTP 404)."""
    status_code = 404
    error_code = "NOT_FOUND"


class ConflictError(AppError):
    """Конфликт состояния ресурса, например дубликат email/артикула или нехватка товара (HTTP 409)."""
    status_code = 409
    error_code = "CONFLICT"
