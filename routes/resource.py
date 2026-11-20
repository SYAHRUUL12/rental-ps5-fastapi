"""
routes/resource.py
Endpoint CRUD lengkap untuk resource utama: Unit / Paket Rental PS5 (/consoles).
"""

from typing import List
from fastapi import APIRouter, HTTPException, Query, status
import database as db
from models import ConsoleCreate, ConsoleUpdate, ConsoleResponse

router = APIRouter(prefix="/consoles", tags=["Consoles (Resource Utama PS5)"])


@router.get("", response_model=List[ConsoleResponse], status_code=status.HTTP_200_OK)
async def list_consoles(
    skip: int = Query(default=0, ge=0, description="Jumlah data yang dilewati (offset)"),
    limit: int = Query(default=10, ge=1, le=100, description="Jumlah maksimum data yang ditampilkan"),
):
    """
    GET /consoles?skip=0&limit=10
    Menampilkan daftar semua unit/paket rental PS5 dengan pagination.
    """
    consoles = await db.get_all_consoles(skip=skip, limit=limit)
    return consoles


@router.get("/{console_id}", response_model=ConsoleResponse, status_code=status.HTTP_200_OK)
async def get_console(console_id: int):
    """
    GET /consoles/{id}
    Menampilkan detail satu unit PS5 berdasarkan ID.
    Mengembalikan 404 Not Found jika ID tidak ditemukan.
    """
    console = await db.get_console_by_id(console_id)
    if not console:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit PS5 dengan ID {console_id} tidak ditemukan.",
        )
    return console


@router.post("", response_model=ConsoleResponse, status_code=status.HTTP_201_CREATED)
async def add_console(payload: ConsoleCreate):
    """
    POST /consoles
    Menambahkan unit/paket rental PS5 baru ke basis data.
    Validasi input dilakukan otomatis oleh model Pydantic ConsoleCreate.
    """
    created = await db.create_console(payload.model_dump())
    return created


@router.put("/{console_id}", response_model=ConsoleResponse, status_code=status.HTTP_200_OK)
async def edit_console(console_id: int, payload: ConsoleUpdate):
    """
    PUT /consoles/{id}
    Memperbarui seluruh informasi unit PS5 berdasarkan ID dan mengembalikan data terbaru.
    """
    updated = await db.update_console(console_id, payload.model_dump())
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit PS5 dengan ID {console_id} tidak ditemukan.",
        )
    return updated


@router.delete("/{console_id}", status_code=status.HTTP_200_OK)
async def remove_console(console_id: int):
    """
    DELETE /consoles/{id}
    Menghapus permanen (hard delete) unit PS5 dari basis data.
    """
    deleted = await db.delete_console(console_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit PS5 dengan ID {console_id} tidak ditemukan.",
        )
    return {
        "message": f"Unit PS5 dengan ID {console_id} berhasil dihapus secara permanen.",
        "deleted_id": console_id,
    }
