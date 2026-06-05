from time import monotonic

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    routes_ai_analysis,
    routes_auth,
    routes_chat,
    routes_dashboard,
    routes_energy_bills,
    routes_knowledge,
    routes_leads,
    routes_proposal_kits,
    routes_proposals,
    routes_tickets,
    routes_whatsapp,
)
from app.core.config import settings

app = FastAPI(
    title="Solar Soluções Solis API",
    description="API para chatbot comercial e técnico da Solar Soluções.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate_limit_bucket: dict[str, list[float]] = {}


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path in {"/health", "/docs", "/openapi.json", "/redoc"}:
        return await call_next(request)

    client = request.client.host if request.client else "unknown"
    now = monotonic()
    window_start = now - 60
    events = [timestamp for timestamp in _rate_limit_bucket.get(client, []) if timestamp >= window_start]
    if len(events) >= settings.rate_limit_per_minute:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Muitas requisições. Tente novamente em instantes."},
        )
    events.append(now)
    _rate_limit_bucket[client] = events
    return await call_next(request)


@app.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


app.include_router(routes_auth.router)
app.include_router(routes_chat.router)
app.include_router(routes_leads.router)
app.include_router(routes_proposals.router)
app.include_router(routes_proposals.price_router)
app.include_router(routes_proposals.company_router)
app.include_router(routes_proposals.public_router)
app.include_router(routes_proposal_kits.router)
app.include_router(routes_tickets.router)
app.include_router(routes_knowledge.router)
app.include_router(routes_dashboard.router)
app.include_router(routes_whatsapp.router)
app.include_router(routes_ai_analysis.router)
app.include_router(routes_energy_bills.router)
