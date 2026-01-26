from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.core.settings import settings
from app.presentation.controllers.portfolio_routes import portfolio_router
from app.presentation.controllers.program_routes import program_router
from app.presentation.controllers.project_routes import projects_router
from app.presentation.controllers.testcase_routes import test_router
from app.presentation.controllers.user_routes import user_router

app = FastAPI(title=settings.app_name)
app.include_router(user_router, prefix=settings.api_prefix)
app.include_router(portfolio_router, prefix=settings.api_prefix)
app.include_router(program_router, prefix=settings.api_prefix)
app.include_router(projects_router, prefix=settings.api_prefix)
app.include_router(test_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
