from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.api.routers import webapp
from src.shared.db import init_db
from src.shared.config import settings

app = FastAPI(title="Hydration API")

# CORS (useful for local dev)
allowed_origins = [o.strip() for o in (settings.ALLOWED_ORIGINS or "").split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = ["*"] if settings.DEV_ALLOW_NO_INITDATA else [settings.WEBAPP_URL]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роуты API
app.include_router(webapp.router)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/health")
async def health():
    return {"status": "ok"}

# Подключаем фронт
app.mount("/", StaticFiles(directory="webapp/dist", html=True), name="frontend")

# Чтобы index.html открывался на /
@app.get("/")
async def serve_frontend():
    return FileResponse("webapp/dist/index.html")