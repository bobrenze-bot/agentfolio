"""
AgentRank Backend - FastAPI Application

Entry point for the FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api import webhooks

app = FastAPI(
    title="AgentRank API",
    description="Live agent rankings and discovery platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include webhook router
app.include_router(webhooks.router)

# Include other routers (to be implemented)
# from app.api import agents, leaderboards, search, verification
# app.include_router(agents.router, prefix="/api/v1")
# app.include_router(leaderboards.router, prefix="/api/v1")
# app.include_router(search.router, prefix="/api/v1")
# app.include_router(verification.router, prefix="/api/v1")
