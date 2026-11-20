"""
seed.py
Skrip inisialisasi data awal (seeding) untuk basis data SQLite Rental PS 5.
Mengisi minimal 10 baris data unit/paket konsol PS5 agar endpoint CRUD dan transaksi
dapat langsung diuji.
"""

import asyncio
from database import init_db, get_db_connection

INITIAL_CONSOLES = [
    {
        "nama_unit": "PS5 Disc Edition - Bilik Reguler 01",
        "tipe_konsol": "PS5 Disc",
        "jumlah_stik": 2,
        "harga_per_jam": 15000.0,
        "stok": 5,
        "deskripsi": "TV LED 43 inch 4K, 2 Stik DualSense, EA FC 25, eFootball, GTA V",
    },
    {
        "nama_unit": "PS5 Disc Edition - Bilik Reguler 02",
        "tipe_konsol": "PS5 Disc",
        "jumlah_stik": 2,
        "harga_per_jam": 15000.0,
        "stok": 4,
        "deskripsi": "TV LED 43 inch 4K, 2 Stik DualSense, Tekken 8, Mortal Kombat 1",
    },
    {
        "nama_unit": "PS5 Digital Edition - Paket Hemat 01",
        "tipe_konsol": "PS5 Digital",
        "jumlah_stik": 2,
        "harga_per_jam": 12000.0,
        "stok": 6,
        "deskripsi": "TV 40 inch Full HD, 2 Stik DualSense, eFootball, Rocket League, Fall Guys",
    },
    {
        "nama_unit": "PS5 Digital Edition - Paket Hemat 02",
        "tipe_konsol": "PS5 Digital",
        "jumlah_stik": 2,
        "harga_per_jam": 12000.0,
        "stok": 5,
        "deskripsi": "TV 40 inch Full HD, 2 Stik DualSense, NBA 2K25, It Takes Two",
    },
    {
        "nama_unit": "PS5 Slim Disc - Paket Mabar 4 Stik",
        "tipe_konsol": "PS5 Slim",
        "jumlah_stik": 4,
        "harga_per_jam": 22000.0,
        "stok": 3,
        "deskripsi": "TV 50 inch 4K HDR, 4 Stik DualSense, EA FC 25, Overcooked! All You Can Eat",
    },
    {
        "nama_unit": "PS5 Pro 2TB - VIP Room AC 01",
        "tipe_konsol": "PS5 Pro",
        "jumlah_stik": 2,
        "harga_per_jam": 30000.0,
        "stok": 2,
        "deskripsi": "Ruang VIP AC + Sofa, Smart TV 65 inch OLED 120Hz, Spider-Man 2, God of War Ragnarok",
    },
    {
        "nama_unit": "PS5 Pro 2TB - VIP Room AC 02",
        "tipe_konsol": "PS5 Pro",
        "jumlah_stik": 4,
        "harga_per_jam": 35000.0,
        "stok": 2,
        "deskripsi": "Ruang VIP AC + Sofa Bed, Smart TV 65 inch OLED 120Hz, 4 Stik DualSense Edge",
    },
    {
        "nama_unit": "PS5 + PlayStation VR2 Bundle",
        "tipe_konsol": "PS5 VR2 Bundle",
        "jumlah_stik": 2,
        "harga_per_jam": 40000.0,
        "stok": 2,
        "deskripsi": "Headset PS VR2 + Sense Controller, Horizon Call of the Mountain, Gran Turismo 7",
    },
    {
        "nama_unit": "PS5 Racing Simulator Cockpit",
        "tipe_konsol": "PS5 Disc",
        "jumlah_stik": 2,
        "harga_per_jam": 35000.0,
        "stok": 2,
        "deskripsi": "Kursi Balap + Steering Wheel Logitech G29, Gran Turismo 7 & F1 24",
    },
    {
        "nama_unit": "PS5 Disc Portable - Sewa Bawa Pulang (Harian)",
        "tipe_konsol": "PS5 Disc",
        "jumlah_stik": 2,
        "harga_per_jam": 10000.0,
        "stok": 4,
        "deskripsi": "Tas hardcase + Kabel HDMI + 2 Stik DualSense (minimal sewa 12 jam bawa pulang)",
    },
    {
        "nama_unit": "PS5 Slim Digital - Sewa Bawa Pulang (Harian)",
        "tipe_konsol": "PS5 Slim",
        "jumlah_stik": 2,
        "harga_per_jam": 8500.0,
        "stok": 5,
        "deskripsi": "Paket bawa pulang ekonomis dengan PS Plus Extra terinstal",
    },
    {
        "nama_unit": "PS5 Turnamen Booth - 120Hz Monitor",
        "tipe_konsol": "PS5 Disc",
        "jumlah_stik": 2,
        "harga_per_jam": 20000.0,
        "stok": 3,
        "deskripsi": "Monitor Gaming 27 inch 144Hz rendah latensi untuk latihan kompetitif Tekken 8 & EA FC",
    },
]


async def seed_database() -> None:
    """Mengosongkan data lama dan mengisi 12 data awal unit PS5 ke SQLite."""
    await init_db()
    db = await get_db_connection()
    try:
        # Reset tabel agar ID mulai rapi dari 1 setiap kali seed.py dijalankan
        await db.execute("DELETE FROM transactions;")
        await db.execute("DELETE FROM consoles;")
        await db.execute("DELETE FROM sqlite_sequence WHERE name IN ('consoles', 'transactions');")

        for item in INITIAL_CONSOLES:
            await db.execute(
                """
                INSERT INTO consoles (nama_unit, tipe_konsol, jumlah_stik, harga_per_jam, stok, deskripsi)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item["nama_unit"],
                    item["tipe_konsol"],
                    item["jumlah_stik"],
                    item["harga_per_jam"],
                    item["stok"],
                    item["deskripsi"],
                ),
            )
        await db.commit()
        print(f"[BERHASIL] {len(INITIAL_CONSOLES)} data unit Rental PS5 berhasil dimasukkan ke rental_ps5.db!")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
