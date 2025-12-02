import logging
import time

from sqlalchemy import event
from sqlalchemy.engine import Engine

# https://docs.sqlalchemy.org/en/20/faq/performance.html

logger = logging.getLogger("freezing.sqltime")
logger.setLevel(logging.DEBUG)


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(
    conn, _cursor, _statement, _parameters, _context, _executemany
):
    conn.info.setdefault("query_start_time", []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, _cursor, statement, _parameters, _context, _executemany):
    total: float = time.time() - conn.info["query_start_time"].pop(-1)
    if total > 0.5:
        logger.warning("SQL query took %f seconds: %s", total, statement)
