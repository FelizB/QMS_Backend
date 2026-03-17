from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.application.services.audit_helper import AuditLogger
from app.infrastructure.models.activity_log import EntityType, ActivityAction


class ErrorAuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, session_factory: async_sessionmaker):
        super().__init__(app)
        self.session_factory = session_factory

    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            # Best-effort context; if you have user via auth, pull it here
            user = getattr(request.state, "user", None)
            org_id = getattr(user, "org_id", None) if user else None
            actor_id = getattr(user, "id", None) if user else None
            first_name = getattr(user, "first_name", None) if user else None

            audit = AuditLogger(session=None, session_factory=self.session_factory,
                                request_id=getattr(request.state, "request_id", None))
            # entity unknown; write generic failure
            await audit.log_failure_fallback(
                org_id=org_id,
                entity_type=EntityType.PROJECT,  # or a special "system" type you add
                entity_id=0,
                action=ActivityAction.UPDATED,  # or "created" based on route if you can detect
                title=f"Unhandled exception at {request.url.path}",
                actor_id=actor_id,
                actor_first_name=first_name,
                error=e,
                metadata={"method": request.method, "path": request.url.path},
            )
            return JSONResponse({"detail": "Internal Server Error"}, status_code=500)
