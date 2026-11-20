"""
database.py
Modul manajemen koneksi basis data SQLite secara asinkron menggunakan aiosqlite,
definisi skema tabel, operasi CRUD, serta mekanisme penguncian konkurensi (asyncio.Lock).
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
import aiosqlite

DB_PATH = "rental_ps5.db"

# Inisialisasi gembok konkurensi (asyncio.Lock) di tingkat modul untuk mencegah
# race condition (overselling) saat beberapa request transaksi masuk secara bersamaan.
stok_lock = asyncio.Lock()

# Skema tabel resource utama: unit/paket konsol PlayStation 5
# Memiliki 6 kolom selain id (syarat minimum: 4 kolom selain id) dan kolom kuantitas 'stok'.
CREATE_CONSOLES_TABLE = """
CREATE TABLE IF NOT EXISTS consoles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_unit TEXT NOT NULL,
    tipe_konsol TEXT NOT NULL,
    jumlah_stik INTEGER NOT NULL DEFAULT 2,
    harga_per_jam REAL NOT NULL,
    stok INTEGER NOT NULL,
    deskripsi TEXT
);
"""

# Skema tabel resource transaksi: penyewaan unit PS5
CREATE_TRANSACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    console_id INTEGER NOT NULL,
    nama_penyewa TEXT NOT NULL,
    qty INTEGER NOT NULL,
    durasi_jam INTEGER NOT NULL DEFAULT 1,
    total_harga REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    FOREIGN KEY (console_id) REFERENCES consoles (id)
);
"""


async def get_db_connection() -> aiosqlite.Connection:
    """
    Membuka koneksi asinkron ke SQLite menggunakan aiosqlite.
    Mengaktifkan row_factory agar hasil query dapat diakses seperti dictionary,
    serta mengaktifkan mode WAL dan busy_timeout agar aman saat dijalankan multi-worker.
    """
    db = await aiosqlite.connect(DB_PATH, timeout=30.0)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA busy_timeout=30000;")
    return db


async def init_db() -> None:
    """Inisialisasi tabel consoles dan transactions pada basis data SQLite."""
    db = await get_db_connection()
    try:
        await db.execute(CREATE_CONSOLES_TABLE)
        await db.execute(CREATE_TRANSACTIONS_TABLE)
        await db.commit()
    finally:
        await db.close()


# ==============================================================================
# OPERASI CRUD RESOURCE UTAMA (CONSOLES / UNIT PS5)
# ==============================================================================

async def get_all_consoles(skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
    """Mengambil daftar unit PS5 dengan pagination (skip & limit) secara non-blocking."""
    db = await get_db_connection()
    try:
        cursor = await db.execute(
            "SELECT * FROM consoles ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, skip),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_console_by_id(console_id: int) -> Optional[Dict[str, Any]]:
    """Mengambil detail satu unit PS5 berdasarkan ID."""
    db = await get_db_connection()
    try:
        cursor = await db.execute("SELECT * FROM consoles WHERE id = ?", (console_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def create_console(data: Dict[str, Any]) -> Dict[str, Any]:
    """Menambahkan unit PS5 baru ke basis data dan mengembalikan data yang tersimpan."""
    db = await get_db_connection()
    try:
        cursor = await db.execute(
            """
            INSERT INTO consoles (nama_unit, tipe_konsol, jumlah_stik, harga_per_jam, stok, deskripsi)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["nama_unit"],
                data["tipe_konsol"],
                data["jumlah_stik"],
                data["harga_per_jam"],
                data["stok"],
                data.get("deskripsi"),
            ),
        )
        await db.commit()
        new_id = cursor.lastrowid
        return await get_console_by_id(new_id)
    finally:
        await db.close()


async def update_console(console_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Memperbarui data unit PS5 berdasarkan ID dan mengembalikan data terbaru."""
    existing = await get_console_by_id(console_id)
    if not existing:
        return None

    db = await get_db_connection()
    try:
        await db.execute(
            """
            UPDATE consoles
            SET nama_unit = ?,
                tipe_konsol = ?,
                jumlah_stik = ?,
                harga_per_jam = ?,
                stok = ?,
                deskripsi = ?
            WHERE id = ?
            """,
            (
                data["nama_unit"],
                data["tipe_konsol"],
                data["jumlah_stik"],
                data["harga_per_jam"],
                data["stok"],
                data.get("deskripsi"),
                console_id,
            ),
        )
        await db.commit()
        return await get_console_by_id(console_id)
    finally:
        await db.close()


async def delete_console(console_id: int) -> bool:
    """Menghapus permanen (hard delete) unit PS5 dari basis data."""
    existing = await get_console_by_id(console_id)
    if not existing:
        return False

    db = await get_db_connection()
    try:
        await db.execute("DELETE FROM consoles WHERE id = ?", (console_id,))
        await db.commit()
        return True
    finally:
        await db.close()


# ==============================================================================
# OPERASI PEMOTONGAN STOK (B3: THREAD / ASYNC SAFETY)
# ==============================================================================

async def get_stok(console_id: int) -> Optional[int]:
    """Membaca jumlah stok terkini dari unit PS5 tertentu."""
    db = await get_db_connection()
    try:
        cursor = await db.execute("SELECT stok FROM consoles WHERE id = ?", (console_id,))
        row = await cursor.fetchone()
        return row["stok"] if row else None
    finally:
        await db.close()


async def decrement_stok(console_id: int, qty: int) -> None:
    """Mengurangi nilai stok unit PS5 sebesar qty di basis data."""
    db = await get_db_connection()
    try:
        await db.execute(
            "UPDATE consoles SET stok = stok - ? WHERE id = ?",
            (qty, console_id),
        )
        await db.commit()
    finally:
        await db.close()


async def potong_stok_tanpa_lock(console_id: int, qty: int) -> bool:
    """
    VERSI 1 (UNSAFE / TANPA LOCK):
    Fungsi pemotongan stok tanpa pengaman asyncio.Lock.
    Digunakan untuk pengujian B3 Tahap 1 guna mendemonstrasikan celah race condition
    (overselling hingga stok bernilai negatif) saat dua request masuk serentak.
    """
    stok_terkini = await get_stok(console_id)
    if stok_terkini is None:
        return False

    # Jeda buatan 10ms untuk membuka jendela waktu terjadinya race condition
    # saat coroutine lain ikut membaca nilai stok sebelum sempat diperbarui.
    await asyncio.sleep(0.01)

    if stok_terkini < qty:
        return False

    # Kedua request yang lolos pengecekan akan mengurangi stok secara bersamaan
    await decrement_stok(console_id, qty)
    return True


async def potong_stok_dengan_lock(console_id: int, qty: int) -> bool:
    """
    VERSI 2 (SAFE / DENGAN ASYNCIO.LOCK):
    Fungsi pemotongan stok aman menggunakan asyncio.Lock.
    Blok 'async with stok_lock:' memastikan hanya satu coroutine yang dapat masuk
    ke critical section (baca stok -> cek kecukupan -> kurangi stok) pada satu waktu.
    """
    async with stok_lock:
        stok_terkini = await get_stok(console_id)
        if stok_terkini is None:
            return False

        # Simulasi jeda I/O di dalam critical section; coroutine lain tetap antre
        # menunggu gembok dilepaskan sehingga tidak terjadi pembacaan stok basi.
        await asyncio.sleep(0.01)

        if stok_terkini < qty:
            return False

        await decrement_stok(console_id, qty)
        return True


# ==============================================================================
# OPERASI TRANSAKSI PENYEWAAN PS5 (B2: ASYNC PROCESSING)
# ==============================================================================

async def insert_transaction(
    console_id: int,
    nama_penyewa: str,
    qty: int,
    durasi_jam: int,
    total_harga: float,
    status: str = "pending",
) -> int:
    """Menyimpan record transaksi baru dengan status awal 'pending'."""
    created_at = datetime.now().isoformat(timespec="seconds")
    db = await get_db_connection()
    try:
        cursor = await db.execute(
            """
            INSERT INTO transactions (console_id, nama_penyewa, qty, durasi_jam, total_harga, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (console_id, nama_penyewa, qty, durasi_jam, total_harga, status, created_at),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def update_trx_status(trx_id: int, new_status: str) -> None:
    """Memperbarui status transaksi (pending -> processing -> completed / failed)."""
    db = await get_db_connection()
    try:
        await db.execute(
            "UPDATE transactions SET status = ? WHERE id = ?",
            (new_status, trx_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_all_transactions(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Mengambil daftar transaksi, mendukung filter opsional berdasarkan status."""
    db = await get_db_connection()
    try:
        if status_filter:
            cursor = await db.execute(
                "SELECT * FROM transactions WHERE status = ? ORDER BY id DESC",
                (status_filter,),
            )
        else:
            cursor = await db.execute("SELECT * FROM transactions ORDER BY id DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_transaction_by_id(trx_id: int) -> Optional[Dict[str, Any]]:
    """Mengambil detail satu transaksi beserta status terkininya berdasarkan ID."""
    db = await get_db_connection()
    try:
        cursor = await db.execute("SELECT * FROM transactions WHERE id = ?", (trx_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()
