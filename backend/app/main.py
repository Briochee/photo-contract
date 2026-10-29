"""FastAPI application entry point for the local Contract Studio."""

from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.app.api import agreements, bookings, clients, dashboard, documents, invoices, settings
from backend.app.config import FRONTEND_DIST
from backend.app.logging_config import activity, requests

app = FastAPI(
    title="Contract Studio",
    version="1.0.0",
    description="Local-first client, booking, agreement, invoice, and document management.",
    docs_url="/docs",
    redoc_url=None,
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "testserver"],
)

for route_module in (clients, agreements, bookings, invoices, documents, settings, dashboard):
    app.include_router(route_module.router)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    """Return actionable validation locations without echoing client-submitted values."""
    details = [
        {"loc": error["loc"], "msg": error["msg"], "type": error["type"]} for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})


@app.exception_handler(IntegrityError)
async def integrity_error(_request: Request, _exc: IntegrityError):
    activity.warning("database_constraint_conflict")
    return JSONResponse(
        status_code=409, content={"detail": "The request conflicts with an existing record"}
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(_request: Request, _exc: SQLAlchemyError):
    activity.error("database_operation_failed")
    return JSONResponse(status_code=500, content={"detail": "The local database operation failed"})


@app.middleware("http")
async def check_browser_origin(request: Request, call_next):
    """Reject cross-site browser writes while allowing local Vite and same-origin use."""
    started = perf_counter()
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin:
            same_origin = origin == f"{request.url.scheme}://{request.url.netloc}"
            allowed_origins = {
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            }
            if not same_origin and origin not in allowed_origins:
                requests.warning("method=%s path=%s status=403", request.method, request.url.path)
                return JSONResponse(
                    status_code=403, content={"detail": "Untrusted local browser origin"}
                )
    try:
        response = await call_next(request)
    except Exception:
        requests.exception("method=%s path=%s outcome=error", request.method, request.url.path)
        raise
    elapsed_ms = round((perf_counter() - started) * 1000)
    requests.info(
        "method=%s path=%s status=%d duration_ms=%d",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/health")
def health():
    return {"status": "ok", "application": "Contract Studio"}


if FRONTEND_DIST.is_dir():
    assets = FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")


@app.get("/{full_path:path}", include_in_schema=False)
def frontend_fallback(full_path: str):
    if full_path == "health" or full_path.startswith("api/"):
        raise HTTPException(404, "Not found")
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        raise HTTPException(404, "Frontend build is missing; run npm run build in frontend/")
    return FileResponse(index)
