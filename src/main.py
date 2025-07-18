import logging
import asyncio
import sys
import nest_asyncio

from fastapi import FastAPI

from src.api.v1.api_router import api_v1_router
from src.core.config import config
from src.core.exceptions import add_exception_handlers
from src.utils.logging import setup_logging

# --- Setup Logging ---
log_level = getattr(config, "LOG_LEVEL", "INFO")
setup_logging(log_level=log_level)
logger = logging.getLogger(__name__)  # This logger will be used by the middleware too
# ---------------------

# Apply nest_asyncio to allow nested event loops
if type(asyncio.get_event_loop()).__module__ != "uvloop.loop":
    nest_asyncio.apply()

# Windows-specific event loop policy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """
#     Lifespan context manager for FastAPI.
#     """
#     pass

app = FastAPI()

app.include_router(api_v1_router, prefix="/v1")

# Add exception handlers
add_exception_handlers(app)


@app.get("/")
async def root():
    return {"message": "Hello World"}
