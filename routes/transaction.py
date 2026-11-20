"""
routes/transaction.py
Endpoint transaksi penyewaan PS5 dengan pemrosesan asinkron di latar belakang
(FastAPI BackgroundTasks) dan pencegahan race condition (asyncio.Lock).
"""

import asyncio
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
import database as db
from models import (
    TransactionCreate,
    TransactionAcceptedResponse,
    TransactionResponse,
)

router = APIRouter(prefix="/transactions", tags=["Transactions (Penyewaan PS5)"])


async def proses_transaksi_background(trx_id: int, console_id: int, qty: int) -> None:
    """
    Fungsi pekerja latar belakang (internal Python coroutine, bukan endpoint HTTP).
    Alur status transaksi: pending -> processing -> completed / failed.
    """
    try:
        # 1. Perbarui status transaksi dari 'pending' menjadi 'processing'
        await db.update_trx_status(trx_id, "processing")

        # 2. Simulasi pemrosesan I/O intensif (misal: verifikasi jadwal & aktivasi billing TV/konsol)
        await asyncio.sleep(3)

        # 3. Finalisasi transaksi dan ubah status menjadi 'completed'
        await db.update_trx_status(trx_id, "completed")
    except Exception:
        # Jika terjadi kegagalan tak terduga saat pemrosesan latar belakang,
        # tandai transaksi sebagai 'failed'.
        await db.update_trx_status(trx_id, "failed")


@router.post(
    "",
    response_model=TransactionAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_transaction(data: TransactionCreate, bg: BackgroundTasks):
    """
    POST /transactions
    Membuat transaksi penyewaan PS5 baru:
    1. Memastikan unit PS5 terdaftar di basis data (jika tidak -> 404 Not Found).
    2. Memotong stok secara aman dengan asyncio.Lock (jika stok habis -> 409 Conflict).
    3. Menyimpan transaksi dengan status 'pending' dan menjadwalkan BackgroundTasks.
    4. Langsung mengembalikan respon 202 Accepted tanpa menunggu proses background selesai.
    """
    # Cek keberadaan resource unit PS5 di basis data
    console = await db.get_console_by_id(data.console_id)
    if not console:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit PS5 dengan ID {data.console_id} tidak ditemukan.",
        )

    # ==========================================================================
    # PENGUJIAN B3 (THREAD / ASYNC SAFETY):
    # - Kondisi Default (Tahap 2 - Aman): gunakan `db.potong_stok_dengan_lock`
    # - Untuk simulasi Tahap 1 (Tanpa Lock / Race Condition): ganti baris di bawah
    #   menjadi `berhasil = await db.potong_stok_tanpa_lock(data.console_id, data.qty)`
    # ==========================================================================
    berhasil = await db.potong_stok_dengan_lock(data.console_id, data.qty)

    if not berhasil:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stok unit '{console['nama_unit']}' tidak mencukupi atau sudah habis.",
        )

    # Hitung total biaya sewa
    total_harga = console["harga_per_jam"] * data.qty * data.durasi_jam

    # Simpan transaksi awal dengan status 'pending'
    trx_id = await db.insert_transaction(
        console_id=data.console_id,
        nama_penyewa=data.nama_penyewa,
        qty=data.qty,
        durasi_jam=data.durasi_jam,
        total_harga=total_harga,
        status="pending",
    )

    # Daftarkan tugas latar belakang agar berjalan setelah respon HTTP dikirim
    bg.add_task(proses_transaksi_background, trx_id, data.console_id, data.qty)

    return TransactionAcceptedResponse(
        id=trx_id,
        console_id=data.console_id,
        nama_penyewa=data.nama_penyewa,
        qty=data.qty,
        durasi_jam=data.durasi_jam,
        total_harga=total_harga,
        status="pending",
        message="Transaksi diterima dan sedang diproses secara asinkron di latar belakang.",
    )


@router.get("", response_model=List[TransactionResponse], status_code=status.HTTP_200_OK)
async def list_transactions(
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter transaksi berdasarkan status (pending, processing, completed, failed)",
    )
):
    """
    GET /transactions
    Menampilkan daftar transaksi penyewaan PS5.
    Mendukung query parameter filter ?status=pending (atau processing/completed/failed).
    """
    transactions = await db.get_all_transactions(status_filter=status_filter)
    return transactions


@router.get("/{trx_id}", response_model=TransactionResponse, status_code=status.HTTP_200_OK)
async def get_transaction_detail(trx_id: int):
    """
    GET /transactions/{id}
    Memantau detail dan status terkini dari satu transaksi penyewaan PS5.
    """
    trx = await db.get_transaction_by_id(trx_id)
    if not trx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaksi dengan ID {trx_id} tidak ditemukan.",
        )
    return trx
