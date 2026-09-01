from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, health, uploads, users, reconcile

app = FastAPI(title="Recon Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(uploads.router)
app.include_router(reconcile.router)


@app.get("/")
async def root():
    return {"message": "Recon Dashboard API"}
