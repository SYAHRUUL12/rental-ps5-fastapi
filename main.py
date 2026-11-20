"""
main.py
Entry point aplikasi REST API Rental PlayStation 5 menggunakan FastAPI.
Mengelola lifecycle inisialisasi basis data SQLite (aiosqlite) dan registrasi router.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import init_db
from routes.resource import router as resource_router
from routes.transaction import router as transaction_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler FastAPI:
    Memastikan tabel SQLite terbentuk secara asinkron sebelum menerima request.
    """
    await init_db()
    yield


app = FastAPI(
    title="API Sistem Rental PlayStation 5",
    description=(
        "REST API asinkron berbasis FastAPI dan aiosqlite untuk manajemen unit konsol PS5 "
        "serta transaksi penyewaan dengan BackgroundTasks dan asyncio.Lock."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Registrasi router resource utama (/consoles) dan transaksi (/transactions)
app.include_router(resource_router)
app.include_router(transaction_router)


@app.get("/", tags=["Health Check"])
async def root():
    """Endpoint pengecekan status server API Rental PS5."""
    return {
        "status": "online",
        "service": "API Sistem Rental PlayStation 5",
        "docs_url": "/docs",
    }
