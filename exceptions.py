class CheckTokensError(Exception):
    """Отсутствуют необходимые токены аутентификации."""


class RequestApiError(Exception):
    """Ошибка запроса к API."""


class ResponseApiError(Exception):
    """Ошибка в ответе API."""


class InvalidJSONError(Exception):
    """Не валидный JSON."""
