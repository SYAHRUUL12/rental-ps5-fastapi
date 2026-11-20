"""
test_race.py
Skrip pengujian mandiri untuk Bagian B3 (Thread/Async Safety).
Mengirimkan 2 request transaksi secara serentak (concurrent) pada milidetik yang sama
ke POST /transactions untuk menguji pencegahan race condition (overselling).

Cara Penggunaan:
1. Pastikan stok unit PS5 ID 1 sudah diatur menjadi 1 di database (atau jalankan dengan argumen --set-stok-1).
2. Jalankan server FastAPI: uvicorn main:app --port 8000
3. Jalankan skrip ini di terminal kedua: python test_race.py
"""

import asyncio
import sys
import aiosqlite
import httpx

BASE_URL = "http://127.0.0.1:8000"
DB_PATH = "rental_ps5.db"


async def reset_stok_unit_1(stok_awal: int = 1) -> None:
    """Helper untuk mengatur stok unit PS5 ID 1 menjadi 1 sebelum pengujian."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE consoles SET stok = ? WHERE id = 1", (stok_awal,))
        await db.commit()
    print(f"[SETUP] Stok Unit PS5 (ID 1) diatur menjadi: {stok_awal}")


async def main() -> None:
    # Jika dijalankan dengan flag --reset, otomatis set stok unit 1 menjadi 1
    if "--reset" in sys.argv:
        await reset_stok_unit_1(1)

    url = f"{BASE_URL}/transactions"
    payload_1 = {
        "console_id": 1,
        "nama_penyewa": "Penyewa Pertama (Rizky)",
        "qty": 1,
        "durasi_jam": 2,
    }
    payload_2 = {
        "console_id": 1,
        "nama_penyewa": "Penyewa Kedua (Dimas)",
        "qty": 1,
        "durasi_jam": 3,
    }

    async with httpx.AsyncClient() as client:
        # Cek stok awal sebelum request
        awal = await client.get(f"{BASE_URL}/consoles/1")
        if awal.status_code == 200:
            print(f"[INFO] Stok awal sebelum race test : {awal.json()['stok']}")

        # Kirim dua request transaksi secara serentak dalam milidetik yang sama
        req1 = client.post(url, json=payload_1)
        req2 = client.post(url, json=payload_2)
        res1, res2 = await asyncio.gather(req1, req2)

        print("-" * 65)
        print("Respon Request 1:", res1.status_code, res1.json())
        print("Respon Request 2:", res2.status_code, res2.json())
        print("-" * 65)

        # Cek stok akhir di basis data setelah kedua request selesai dieksekusi
        akhir = await client.get(f"{BASE_URL}/consoles/1")
        if akhir.status_code == 200:
            stok_akhir = akhir.json()["stok"]
            print(f"[HASIL] Stok akhir Unit PS5 (ID 1) : {stok_akhir}")
            if stok_akhir < 0:
                print("[STATUS] TERJADI RACE CONDITION (OVERSELLING)! Stok menjadi negatif.")
            else:
                print("[STATUS] AMAN! Race condition berhasil dicegah oleh asyncio.Lock.")


if __name__ == "__main__":
    asyncio.run(main())
