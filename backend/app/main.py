from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.database import engine, Base, run_migrations
from backend.app.schemas.schemas import HealthResponse
from backend.app.api.endpoints import router as api_router

# Automatically run schema migrations on startup
run_migrations()

app = FastAPI(
    title="RecoverAI",
    description="Razorpay Buildathon — Track 03: AI Revenue Recovery Backend",
    version="1.0.0"
)

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "ok",
        "service": "RecoverAI"
    }

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=True)
