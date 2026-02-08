from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.api.endpoints import router as api_router
from app.db.postgres import init_db
from app.core.limiter import limiter
import logging
import os
from datetime import datetime

# Setup Logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = os.path.join(log_dir, f"app_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Starting application, logging to {log_filename}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173", # Vite default
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
def on_startup():
    init_db()
    # redis warmup could go here
    
    # Process "uploads" folder on startup
    from app.services.ingestion import ingestion_service
    from app.db.postgres import SessionLocal
    import os
    
    db = SessionLocal()
    try:
        upload_dir = "uploads"
        logger.info(f"Check for existing uploads in {upload_dir}...")
        ingestion_service.process_all_in_dir(upload_dir, db)
    except Exception as e:
        logger.error(f"Startup ingestion failed: {e}")
    finally:
        db.close()

@app.get("/health")
def health_check():
    return {"status": "ok"}
