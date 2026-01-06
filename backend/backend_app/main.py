from fastapi import FastAPI
from backend_app.api.v1 import users, auth

app = FastAPI(title="Enterprise API Backend")

# Register routers
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])