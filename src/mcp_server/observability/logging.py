import logging
import re

_KEY_RE = re.compile(r"(serviceKey=)[^&\s\"']+", re.IGNORECASE)


class RedactKeyFilter(logging.Filter):
    def __init__(self, api_key: str) -> None:
        super().__init__()
        self.api_key = api_key

    def filter(self, record: logging.LogRecord) -> bool:
        message = _KEY_RE.sub(r"\1[REDACTED]", record.getMessage())
        if self.api_key:
            message = message.replace(self.api_key, "[REDACTED]")
        record.msg = message
        record.args = ()
        return True


def configure_logging(api_key: str) -> None:
    """Install secret redaction on application and dependency loggers."""
    redaction_filter = RedactKeyFilter(api_key)
    for logger_name in (
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "httpx",
        "mcp_server",
        "mcp_server.clients.wellness",
        "mcp_server.services.wellness",
    ):
        logging.getLogger(logger_name).addFilter(redaction_filter)