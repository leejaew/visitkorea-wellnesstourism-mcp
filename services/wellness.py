import logging
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from api import WellnessAPIError, WellnessClient

logger = logging.getLogger(__name__)


class WellnessService:
    def __init__(self, client: WellnessClient) -> None:
        self.client = client

    async def call(
        self, operation: Callable[..., Awaitable[dict]], **kwargs: Any
    ) -> dict:
        try:
            return await operation(**kwargs)
        except ValueError as exc:
            return {"error": True, "code": "INVALID_PARAM", "message": str(exc)}
        except WellnessAPIError as exc:
            return {"error": True, "code": exc.code, "message": exc.message}
        except Exception as exc:
            # Do not log exception messages or tracebacks here. Unexpected
            # upstream exceptions may contain a request URL with the API key.
            logger.error(
                "Unexpected wellness service failure type=%s",
                type(exc).__name__,
            )
            return {
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": "The request could not be completed.",
            }

    async def invoke(self, operation_name: str, **kwargs: Any) -> dict:
        operation = getattr(self.client, operation_name)
        return await self.call(operation, **kwargs)


_service: Optional[WellnessService] = None


def configure_service(service: WellnessService) -> None:
    global _service
    _service = service


def get_service() -> WellnessService:
    if _service is None:
        raise RuntimeError("Wellness service has not been configured.")
    return _service