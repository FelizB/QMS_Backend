from fastapi import FastAPI
from app.core.settings import settings
from app.presentation.controllers.user_routes import router as user_router
from fastapi.responses import RedirectResponse

app = FastAPI(title=settings.app_name)
app.include_router(user_router, prefix=settings.api_prefix)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
