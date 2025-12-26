import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from app.routes import user, card, transaction, category_override, report, grocery_category, shopping_category, auth, family, logs, billing, feature_request, user_session, two_factor_auth, trusted_device, user_preferences, manual_transaction, upload, plaid
from app.core.cache import get_cache

# Set the full path to the .env file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOTENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path=DOTENV_PATH)

app = FastAPI()

# Add request logging middleware for debugging
@app.middleware("http")
async def log_requests(request, call_next):
    import logging
    logger = logging.getLogger("uvicorn.access")
    path = request.url.path
    method = request.method
    logger.info(f"🔍 INCOMING REQUEST: {method} {path}")
    
    # Check if this is a Plaid route
    if "/plaid" in path:
        logger.info(f"   ✅ This is a Plaid route!")
        logger.info(f"   📋 Available routes: {[r.path for r in app.routes if hasattr(r, 'path') and '/plaid' in r.path]}")
    
    response = await call_next(request)
    logger.info(f"   📤 RESPONSE: {response.status_code} for {method} {path}")
    return response

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],  # Frontend origins
    allow_credentials=True,  # Allow credentials for cookies
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Add session middleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("JWT_SECRET", "your-secret-key-here")
)

app.include_router(user_session.router)  # Must be before user.router to avoid route conflicts
app.include_router(two_factor_auth.router)  # Must be before user.router to avoid route conflicts
app.include_router(trusted_device.router)  # Trusted device routes
app.include_router(user.router)
app.include_router(card.router)
app.include_router(transaction.router)
app.include_router(manual_transaction.router)  # Manual transaction routes
app.include_router(category_override.router)
app.include_router(report.router)
app.include_router(grocery_category.router)
app.include_router(shopping_category.router)
app.include_router(auth.router)
app.include_router(family.router)
app.include_router(logs.router)
app.include_router(billing.router)
app.include_router(feature_request.router)
app.include_router(user_preferences.router)
app.include_router(upload.router)
app.include_router(plaid.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    """Initialize Redis connection, logging service, and Plaid sync scheduler on startup"""
    try:
        # Initialize cache
        cache = get_cache()
        # Test Redis connection (but don't fail if it's not available)
        try:
            await cache.get_redis()
            print("SUCCESS: Redis cache initialized successfully")
        except Exception as redis_error:
            print(f"WARNING: Redis connection failed: {redis_error}")
            print("WARNING: App will continue without caching")
    except Exception as e:
        print(f"ERROR: Cache initialization failed: {e}")
    
    try:
        # Initialize logging service
        from app.services.logging_service import logging_service
        await logging_service.start()
        print("✅ Logging service initialized successfully")
    except Exception as e:
        print(f"⚠️  Logging service initialization failed: {e}")
        print("⚠️  App will continue without system logging")
    
    try:
        # Initialize Plaid sync scheduler
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from app.services.plaid_sync_job import run_daily_sync
        
        scheduler = AsyncIOScheduler()
        # Schedule daily sync at 2 AM
        scheduler.add_job(run_daily_sync, 'cron', hour=2, minute=0, id='plaid_daily_sync')
        scheduler.start()
        print("✅ Plaid sync scheduler initialized successfully (daily at 2 AM)")
        
        # Store scheduler in app state for cleanup
        app.state.scheduler = scheduler
    except Exception as e:
        print(f"⚠️  Plaid sync scheduler initialization failed: {e}")
        print("⚠️  App will continue without automatic sync")

@app.on_event("shutdown")
async def shutdown_event():
    """Close Redis connection, logging service, and scheduler on shutdown"""
    try:
        from app.core.cache import cleanup_cache
        await cleanup_cache()
        print("✅ Redis connection closed")
    except Exception as e:
        print(f"⚠️  Error closing Redis connection: {e}")
    
    try:
        # Stop logging service
        from app.services.logging_service import logging_service
        await logging_service.stop()
        print("✅ Logging service stopped")
    except Exception as e:
        print(f"⚠️  Error stopping logging service: {e}")
    
    try:
        # Stop scheduler
        if hasattr(app.state, 'scheduler'):
            app.state.scheduler.shutdown()
            print("✅ Plaid sync scheduler stopped")
    except Exception as e:
        print(f"⚠️  Error stopping scheduler: {e}") 