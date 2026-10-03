# SouthCity Automation - Matching GL & Working Paper

Skrip Python untuk otomatisasi proses matching transaksi settlement Uang Muka (Advances) antara data General Ledger (GL) dan Working Paper monitoring. Hasil matching diekspor ke Google Sheets, lengkap dengan Executive Summary yang digenerate oleh Gemini AI.

## Cara Kerja

1. Baca semua transaksi **KREDIT** dari file GL (settlement/realisasi)
2. Cocokkan (matching) ke baris Working Paper berdasarkan **nomor PO** atau **kemiripan deskripsi**
3. Isi otomatis kolom Realization Date, No Voucher, Amount, dan hitung Saldo
4. Generate **Executive Summary** via Gemini API
5. Tulis semua hasilnya ke Google Sheets (sheet `Working_Paper_Result` + `Dashboard`)

## Struktur Project

```
southcity-automation-test/
├── main.py                     # Entry point, jalankan ini
├── modules/
│   ├── data_extractor.py       # Baca & bersihkan data dari Excel
│   ├── matcher.py              # Logika matching (Regex + Fuzzy)
│   ├── ai_agent.py             # Panggil Gemini API untuk summary
│   └── sheet_exporter.py       # Ekspor ke Google Sheets
├── data/                       # Taruh file Excel di sini
├── credentials.json            # Service Account key (jangan di-commit)
├── .env                        # API key & config
└── requirements.txt
```

## Setup & Instalasi

### 1. Clone & buat virtual environment

```bash
git clone https://github.com/Dzakiamriz22/south-city-test.git
cd south-city-test
python -m venv venv
```

Aktivasi venv:
- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

```bash
pip install -r requirements.txt
```

### 2. Siapkan file `.env`

```env
GEMINI_API_KEY="isi_api_key_gemini"
GOOGLE_SHEETS_CREDENTIALS_PATH="credentials.json"
SPREADSHEET_ID="isi_id_spreadsheet_target"
```

### 3. Siapkan credentials

- Buat Service Account di Google Cloud Console
- Enable Google Sheets API & Google Drive API
- Download key-nya sebagai `credentials.json`, taruh di root project
- Share spreadsheet target ke email Service Account sebagai Editor

### 4. Taruh file data

Letakkan 2 file Excel ke folder `data/`:
- `GL - Advances Other - April 2026.xls`
- `Working Paper Advances and Prepayment-Soal.xlsx`

### 5. Jalankan

```bash
python main.py
```

## Logika Matching

Setiap transaksi Kredit di GL itu adalah "bukti settlement" — artinya ada uang muka yang dilunasi. Tapi datanya gak langsung nyambung ke Working Paper, jadi perlu dicocokkan. Matching-nya pakai 2 tahap:

### Tahap 1: Regex PO Number (prioritas utama)

Banyak transaksi punya kode PO/WO di deskripsinya. Kode ini unik dan bisa dipakai sebagai "kunci" pencocokan.

**Cara kerjanya:**
1. Scan deskripsi GL dan Working Paper pakai regex pattern `[A-Z0-9]+/[A-Z0-9]+/\d+`
2. Kalau ketemu PO number yang sama di kedua sisi → langsung match

**Contoh konkret dari data:**

```
GL Kredit:
  "TP01/PO/26010005 FURNITURE SHOW UNIT APARTEMEN THE PARC SM 1132..."
                     ↓ regex extract
              TP01/PO/26010005

Working Paper:
  "TP01/PO/26010005 FURNITURE SHOW UNIT APARTEMEN THE PARC SM 1132 - BAR STOOL"
                     ↓ regex extract
              TP01/PO/26010005

Hasil: MATCH ✓ (PO sama persis)
→ Isi Realization Date, No Voucher, Amount dari baris GL ini
```

Transaksi yang berhasil di-match via PO: `TP01/PO/26010005`, `FR01/PO/26010011`, `FR01/PO/26010007`, `HLJC/PO/26030003`, `HLJC/PO/26030002`, `TP01/PO/26010003`.

### Tahap 2: Fuzzy String Matching (fallback)

Gak semua transaksi punya kode PO. Contohnya "PELUNASAN TAGIHAN DROPBOX" atau "TALENTA - BUSSINES FLAT FOR 4 MONTHS". Untuk kasus ini, pakai fuzzy matching — bandingin kemiripan teks deskripsinya.

**Library:** RapidFuzz (C-based, jauh lebih cepat dari FuzzyWuzzy)

**Scorer:** `token_set_ratio` — ini yang paling cocok karena:
- Gak peduli urutan kata (jadi "BUKA PUASA KARYAWAN" dan "KARYAWAN BUKA PUASA" tetap match)
- Gak peduli ada kata tambahan (jadi kalau GL punya deskripsi lebih panjang, tetap bisa match)
- Fokusnya di kesamaan "kumpulan kata", bukan urutan karakter

**Threshold:** 85% — cukup ketat supaya gak salah match, tapi cukup longgar buat nampung variasi penulisan.

**Contoh konkret:**

```
GL Kredit:
  "PELUNASAN TAGIHAN DROPBOX PERIODE 11/3/2026 - 11/3/2027"

Working Paper:
  "ADVANCE PEMBAYARAN KARTU KREDIT BCA UNTUK TAGIHAN DROPBOX PERIODE 11/3/2026 - 11/3/2027"

Skor token_set_ratio: ~90% → di atas threshold 85%
Hasil: MATCH ✓
```

```
GL Kredit:
  "PEMBAYARAN TALENTA BUSSINES FLAT FOR 4 MONTHS TERM-3"

Working Paper:
  "TALENTA - BUSSINES FLAT FOR 4 MONTHS (TERM-3) PERIODE 15 FEBRUARI 2026 - 14 JUNI 2026"

Skor token_set_ratio: ~88% → MATCH ✓
```

### Alur Keseluruhan

```
Untuk setiap transaksi Kredit di GL:
│
├─ Apakah deskripsinya mengandung kode PO?
│   ├─ YA → Cari WP yang punya PO sama
│   │        ├─ Ketemu → MATCH
│   │        └─ Gak ketemu → skip (PO-nya mungkin bukan dari WP ini)
│   │
│   └─ TIDAK → Fuzzy match ke semua deskripsi WP
│              ├─ Skor >= 85% → MATCH
│              └─ Skor < 85% → skip (beda transaksi)
│
└─ Kalau MATCH:
    ├─ Pertama kali match ke WP row ini → simpan date, voucher, amount
    └─ Sudah pernah match (multi-voucher) → tambahkan ke yang sudah ada
```

### Multi-Voucher Settlement

Kadang 1 advance diselesaikan oleh lebih dari 1 voucher kredit. Contoh: advance furniture bisa dilunasi dalam 2 tahap pembayaran.

Pakai pendekatan **Single Row**:
- Nomor voucher digabung pakai koma → `ADV/BK/2604/0001, ADV/BK/2604/0002`
- Tanggal digabung (yang unik saja, di-sort) → `2026-04-07, 2026-04-14`
- Amount dijumlahkan → total dari semua voucher kredit

Pendekatan ini dipilih karena lebih simpel dan gak perlu insert row yang bisa menggeser struktur Working Paper.

## AI Integration

Pakai **Google Gemini API** (model `gemini-3.5-flash`, free tier) untuk generate Executive Summary. Data yang dikirim ke AI:
- Total advance awal, total settled, total unsettled
- Daftar transaksi yang masih gantung

Output AI ditaruh di sheet `Dashboard` bersama Kontrol Panel yang menampilkan metrik KPI (settlement rate, jumlah settled/unsettled, dll).

## Output di Google Sheets

| Sheet | Isi |
|-------|-----|
| `Working_Paper_Result` | Tabel hasil matching — kolom E-H terisi otomatis |
| `Dashboard` | Kontrol Panel (KPI) + Executive Summary dari AI |

## Tech Stack

- Python 3.10
- pandas + openpyxl + xlrd (data processing)
- RapidFuzz (fuzzy matching)
- google-genai SDK (Gemini API)
- gspread + gspread-formatting (Google Sheets)
- python-dotenv (environment config)

## Pemanfaatan AI Coding Assistant

Project ini dikerjakan dengan bantuan **Google Antigravity** (AI Coding Assistant berbasis Gemini). AI dipakai cukup intensif dari awal sampai akhir:

- **Planning**: Bantu tentukan flow, tech stack, dan struktur folder project
- **Setup**: Scaffolding modul-modul, konfigurasi environment, requirements
- **Coding**: Bantu tulis logika matching, data cleaning, prompt engineering, dan integrasi Google Sheets
- **Debugging**: Fix error runtime (SyntaxError, TypeError, model deprecated), resolve warning Pylance
- **Dokumentasi**: Bantu susun README ini

Peran saya lebih ke memahami konteks soal, mengarahkan keputusan desain, validasi output, dan memastikan hasilnya sesuai spesifikasi. AI berfungsi sebagai co-developer yang mempercepat proses pengerjaan.
