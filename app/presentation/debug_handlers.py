import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import PlainTextResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_422_UNPROCESSABLE_ENTITY


def install_debug_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Detailed logs in console
        print("=== RequestValidationError ===")
        print(f"Path   : {request.url.path}")
        try:
            # Avoid dumping large headers; print critical ones
            print(f"Headers: Authorization={request.headers.get('authorization')}, "
                  f"Content-Type={request.headers.get('content-type')}, "
                  f"X-Tenant={request.headers.get('x-tenant')}")
        except Exception:
            pass
        print(f"Detail : {exc.errors()}")
        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,  # keep as 422 for validation
            content={"detail": exc.errors()},
        )

    @app.middleware("http")
    async def error_logging_middleware(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            # Catch anything not handled, log full traceback
            print("=== Unhandled Exception ===")
            print(f"Path   : {request.url.path}")
            try:
                print(f"Headers: Authorization={request.headers.get('authorization')}, "
                      f"Content-Type={request.headers.get('content-type')}, "
                      f"X-Tenant={request.headers.get('x-tenant')}")
            except Exception:
                pass
            traceback.print_exc()
            return PlainTextResponse(
                "Internal Server Error",
                status_code=HTTP_500_INTERNAL_SERVER_ERROR
            )
