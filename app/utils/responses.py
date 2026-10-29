from flask import jsonify


def success_response(data=None, message: str | None = None, status_code: int = 200, meta: dict | None = None):
    """Формирует стандартизированный JSON-ответ для успешных операций."""
    payload = {"status": "success"}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    if meta is not None:
        payload["meta"] = meta
    return jsonify(payload), status_code


def error_response(error_code: str, message: str, status_code: int = 400, details: dict | None = None):
    """Формирует стандартизированный JSON-ответ при возникновении ошибки."""
    payload = {
        "status": "error",
        "error": {
            "code": error_code,
            "message": message,
        }
    }
    if details:
        payload["error"]["details"] = details
    return jsonify(payload), status_code
