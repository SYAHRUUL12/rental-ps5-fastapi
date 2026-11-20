# API Sistem Rental PlayStation 5 (FastAPI + aiosqlite)
LINK YT: https://youtu.be/QuozniCaf6Q?si=WlUuqrebD-_lhHT7
Aplikasi REST API asinkron untuk manajemen unit/paket konsol **Rental PlayStation 5** dan pemrosesan transaksi penyewaan secara latar belakang (*background processing*) dengan proteksi konkurensi `asyncio.Lock`.

## Fitur Utama
- **CRUD Resource Utama (`/consoles`)**: Manajemen unit dan paket rental PS5 secara asinkron menggunakan `aiosqlite` dengan validasi **Pydantic**.
- **Transaksi Asinkron (`/transactions`)**: Pembuatan transaksi penyewaan yang langsung mengembalikan status `202 Accepted` (`pending`), kemudian diproses di latar belakang menggunakan `FastAPI BackgroundTasks` (`pending` → `processing` → `completed` / `failed`).
- **Thread / Async Safety (`asyncio.Lock`)**: Pencegahan *race condition* (*overselling*) saat pemotongan stok unit PS5 secara bersamaan.
- **Load Testing (`Locust`)**: Pengujian performa perbandingan 1 worker vs 4 worker Uvicorn.

---

## Struktur Direktori
```text
project/
├── main.py                 # Inisialisasi FastAPI dan registrasi router
├── database.py             # Koneksi aiosqlite, skema SQLite, dan asyncio.Lock
├── models.py               # Skema validasi Pydantic (request & response)
├── routes/
│   ├── __init__.py
│   ├── resource.py         # Endpoint CRUD unit rental PS5 (/consoles)
│   └── transaction.py      # Endpoint transaksi penyewaan asinkron (/transactions)
├── seed.py                 # Skrip inisialisasi 12 data awal unit PS5
├── test_race.py            # Skrip pengujian race condition (B3)
├── locustfile.py           # Skenario load testing Locust (C1)
├── requirements.txt        # Daftar pustaka dependensi Python
├── README.md               # Panduan instalasi dan eksekusi
└── docs/                   # Dokumentasi & tangkapan layar hasil pengujian
```

---

## Panduan Instalasi & Eksekusi

### 1. Persyaratan Sistem
- **Python 3.10+**
- `pip` (Python Package Manager)

### 2. Instalasi Dependensi
```bash
# Buat virtual environment (opsional namun disarankan)
python -m venv venv

# Aktifkan virtual environment
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install seluruh library yang dibutuhkan
pip install -r requirements.txt
```

### 3. Inisialisasi Data Awal (`seed.py`)
Jalankan perintah berikut untuk membuat basis data `rental_ps5.db` dan mengisi 12 data awal unit PS5:
```bash
python seed.py
```

### 4. Menjalankan Server FastAPI
```bash
uvicorn main:app --reload --port 8000
```
Dokumentasi interaktif Swagger UI dapat diakses melalui browser di:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

---

## Panduan Pengujian

### A. Pengujian Race Condition (`test_race.py` – Bagian B3)
1. **Tahap 1 (Tanpa Lock)**:
   - Ubah pemanggilan di `routes/transaction.py` menjadi `await db.potong_stok_tanpa_lock(data.console_id, data.qty)`.
   - Jalankan server: `uvicorn main:app --port 8000`
   - Pada terminal kedua, jalankan: `python test_race.py --reset`
   - Kedua request akan mengembalikan status `202` dan stok akhir menjadi `-1` (*overselling*).
2. **Tahap 2 (Dengan `asyncio.Lock`)**:
   - Kembalikan pemanggilan di `routes/transaction.py` menjadi `await db.potong_stok_dengan_lock(data.console_id, data.qty)`.
   - Pada terminal kedua, jalankan: `python test_race.py --reset`
   - Hanya satu transaksi yang mendapat status `202 Accepted`, sedangkan transaksi kedua ditolak dengan status `409 Conflict` dan stok akhir tetap `0`.

### B. Pengujian Beban Multi-Worker (`locustfile.py` – Bagian C1)
1. **Jalankan Server (1 Worker atau 4 Worker)**:
   ```bash
   # 1 Worker:
   uvicorn main:app --workers 1 --port 8000

   # 4 Worker:
   uvicorn main:app --workers 4 --port 8000
   ```
2. **Jalankan Locust Web UI**:
   ```bash
   locust -f locustfile.py --host http://127.0.0.1:8000
   ```
   Buka `http://localhost:8089` di browser untuk menjalankan skenario:
   - **Skenario Read**: `GET /consoles` (100 request, 20 users)
   - **Skenario Write**: `POST /transactions` (50 request, 10 users)
