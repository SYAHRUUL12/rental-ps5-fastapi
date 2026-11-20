"""
models.py
Definisi skema validasi request dan serialisasi response menggunakan Pydantic.
"""

from typing import Optional
from pydantic import BaseModel, Field


# ==============================================================================
# MODEL PYDANTIC UNTUK RESOURCE UTAMA (UNIT / PAKET RENTAL PS5)
# ==============================================================================

class ConsoleBase(BaseModel):
    nama_unit: str = Field(..., min_length=3, max_length=100, examples=["PS5 Disc Edition - Paket Reguler"])
    tipe_konsol: str = Field(..., min_length=3, max_length=50, examples=["PS5 Disc"])
    jumlah_stik: int = Field(default=2, ge=1, le=4, examples=[2])
    harga_per_jam: float = Field(..., gt=0, examples=[15000.0])
    stok: int = Field(..., ge=0, description="Jumlah unit/slot PS5 yang tersedia", examples=[5])
    deskripsi: Optional[str] = Field(
        default=None,
        max_length=255,
        examples=["Termasuk 2 DualSense, TV 4K 50 inch, EA FC 25 & GTA V"],
    )


class ConsoleCreate(ConsoleBase):
    """Skema payload untuk menambahkan unit PS5 baru (POST /consoles)."""
    pass


class ConsoleUpdate(ConsoleBase):
    """Skema payload untuk memperbarui data unit PS5 (PUT /consoles/{id})."""
    pass


class ConsoleResponse(ConsoleBase):
    """Skema response serialisasi data unit PS5 dari basis data."""
    id: int

    class Config:
        from_attributes = True


# ==============================================================================
# MODEL PYDANTIC UNTUK RESOURCE TRANSAKSI PENYEWAAN PS5
# ==============================================================================

class TransactionCreate(BaseModel):
    """Skema payload untuk membuat transaksi penyewaan unit PS5 (POST /transactions)."""
    console_id: int = Field(..., gt=0, description="ID unit PS5 yang akan disewa", examples=[1])
    nama_penyewa: str = Field(default="Pelanggan Walk-In", min_length=2, max_length=100, examples=["Budi Santoso"])
    qty: int = Field(..., gt=0, description="Jumlah unit PS5 yang disewa", examples=[1])
    durasi_jam: int = Field(default=2, gt=0, le=24, description="Durasi sewa dalam jam", examples=[2])


class TransactionAcceptedResponse(BaseModel):
    """Skema response instan (202 Accepted) saat transaksi masuk antrean latar belakang."""
    id: int
    console_id: int
    nama_penyewa: str
    qty: int
    durasi_jam: int
    total_harga: float
    status: str
    message: str


class TransactionResponse(BaseModel):
    """Skema response lengkap detail transaksi dan status terkini."""
    id: int
    console_id: int
    nama_penyewa: str
    qty: int
    durasi_jam: int
    total_harga: float
    status: str
    created_at: str

    class Config:
        from_attributes = True
