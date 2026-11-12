"""Domain errors use stable codes without exposing SQL or service credentials."""

from __future__ import annotations


class AppException(Exception):
    def __init__(
        self, detail: str, status: int = 400, code: str = "invalid_request"
    ) -> None:
        super().__init__(detail)
        self.detail, self.status, self.code = detail, status, code


class ForbiddenException(AppException):
    def __init__(self, detail: str = "No tienes permisos para esta consulta.") -> None:
        super().__init__(detail, 403, "forbidden")


class NotFoundException(AppException):
    def __init__(self, detail: str = "No se encontró el recurso.") -> None:
        super().__init__(detail, 404, "not_found")
