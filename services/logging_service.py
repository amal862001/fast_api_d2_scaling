import structlog
import logging
from middleware.request_id import request_id_ctx


def add_request_context(logger, method, event_dict):
    event_dict["request_id"] = request_id_ctx.get("")
    return event_dict


def configure_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            add_request_context,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class   = structlog.stdlib.BoundLogger,
        context_class   = dict,
        logger_factory  = structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use = True,
    )
    # suppress SQLAlchemy INFO logs in production
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str = __name__):
    return structlog.get_logger(name)