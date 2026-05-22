import contextvars
import logging
import time
import uuid
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from src.api.routes import api_router
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.core.database import get_db
import uvicorn

request_id_ctx = contextvars.ContextVar("request_id", default="-")

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_ctx.get()
        return True

logger = logging.getLogger("books-api")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(request_id)s] - %(message)s')
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    logger.addHandler(handler)

app = FastAPI(title="books management API")

@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_ctx.set(req_id)
    
    logger.info(f"Request started: {request.method} {request.url.path}")
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Request finished: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {process_time:.3f}s")
        response.headers["X-Request-ID"] = req_id
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request failed: {request.method} {request.url.path} - Error: {str(e)} - Duration: {process_time:.3f}s", exc_info=True)
        raise e
    finally:
        request_id_ctx.reset(token)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = request_id_ctx.get()
    logger.error(f"Unhandled exception occurred: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": req_id
        }
    )

app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "database": str(e)}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)