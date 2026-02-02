from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.status import HTTP_409_CONFLICT, HTTP_400_BAD_REQUEST, HTTP_422_UNPROCESSABLE_ENTITY

from app.core.settings import settings
from app.domain.errors import OwnershipError, DomainError
from app.presentation.controllers.analytics_router import analytics_router
from app.presentation.controllers.file_routes import file_router
from app.presentation.controllers.portfolio_routes import portfolio_router
from app.presentation.controllers.program_routes import program_router
from app.presentation.controllers.project_routes import projects_router
from app.presentation.controllers.testcase_routes import test_router
from app.presentation.controllers.testcase_routes import testcase_router
from app.presentation.controllers.teststep_routes import step_router
from app.presentation.controllers.user_routes import user_router
from app.presentation.debug_handlers import install_debug_handlers

app = FastAPI(title=settings.app_name)
app.include_router(user_router, prefix=settings.api_prefix)
app.include_router(portfolio_router, prefix=settings.api_prefix)
app.include_router(program_router, prefix=settings.api_prefix)
app.include_router(projects_router, prefix=settings.api_prefix)
app.include_router(test_router, prefix=settings.api_prefix)
app.include_router(step_router, prefix=settings.api_prefix)
app.include_router(testcase_router, prefix=settings.api_prefix)
app.include_router(file_router, prefix=settings.api_prefix)
app.include_router(analytics_router, prefix=settings.api_prefix)
install_debug_handlers(app)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


"""
@app.on_event("startup")
def debug_openapi():
    print("🔍 Checking routes one by one...\n")

    for route in app.routes:
        try:
            print(f"Checking route: {route.path}")
            get_openapi(
                title="debug",
                version="1.0",
                routes=[route],  # only one route at a time
            )
        except Exception as e:
            print(f"\n💥 BROKEN ROUTE: {route.path}")
            print(route.endpoint)
            raise e
"""


@app.exception_handler(OwnershipError)
async def ownership_error_handler(request: Request, exc: OwnershipError):
    return JSONResponse(status_code=HTTP_409_CONFLICT, content={"detail": str(exc)})


# Optional: a catch-all for DomainError
@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(status_code=HTTP_409_CONFLICT, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"detail": str(exc)})
