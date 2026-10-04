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

Setiap transaksi Kredit di GL merupakan bukti settlement/realisasi atas uang muka yang pernah dikeluarkan. Sistem menggunakan arsitektur pencocokan bertingkat (3-Layer Matching Engine):

### Tahap 1: Regex PO / WO Number (Prioritas Utama — Deterministic)

Transaksi pengadaan resmi memiliki nomor Purchase Order (PO) atau Work Order (WO) yang unik di deskripsinya.

**Cara kerjanya:**
1. Ekstraksi kode PO/WO menggunakan regex pattern:
   ```python
   r'\b[A-Z][A-Z0-9]*/(?:PO|WO)/\d+\b'
   ```
   Pattern ini mewajibkan segmen tengah berupa `PO` atau `WO` (contoh: `TP01/PO/26010005`, `HLJC/PO/26030003`), sehingga string lain seperti tanggal `11/3/2026` tidak salah terdeteksi sebagai PO.
2. Jika GL dan Working Paper memiliki kode PO/WO yang sama persis $\rightarrow$ langsung di-match dengan akurasi 100%.

Transaksi yang berhasil di-match via PO: `TP01/PO/26010005`, `FR01/PO/26010011`, `FR01/PO/26010007`, `HLJC/PO/26030003`, `HLJC/PO/26030002`, `TP01/PO/26010003`.

### Tahap 2: Fuzzy String Matching (Fallback — RapidFuzz 85%)

Untuk transaksi tanpa nomor PO atau baris Working Paper yang belum memiliki PO (contoh: Dropbox, Talenta, Sewa Space, Buka Puasa, Complimentary Show Unit, serta Styling Apartemen):

- **Library:** RapidFuzz (C++ engine, sangat cepat dan hemat memori).
- **Text Normalization:** Menghilangkan kata administratif umum (`PELUNASAN`, `PENGEMBALIAN`, `DANA`, `UM`) dan referensi kode kurung agar fokus pada nama project.
- **Scorer:** `token_set_ratio` dengan **Threshold 85%** — mengabaikan perbedaan urutan kata dan informasi pelengkap.
- **Safety Guards:**
  * Validasi periode bulan: mencegah transaksi pelunasan bulan April tertukar dengan uang muka bulan Maret.
  * Validasi sisa saldo: memastikan nilai realisasi tidak melompat melebihi sisa saldo advance terkait.

Contoh kecocokan fuzzy:
- GL `"PELUNASAN TAGIHAN DROPBOX PERIODE 11/3/2026 - 11/3/2027"` $\rightarrow$ WP `"ADVANCE PEMBAYARAN KARTU KREDIT BCA UNTUK TAGIHAN DROPBOX..."` (Skor: >88%)
- GL `"FR01/PO/26010009 PAKET MEETING DI KIRANA RESTO & CAFE"` $\rightarrow$ WP `"PAKET MEETING DI KIRANA RESTO & CAFE"` (Skor: 100%)
- GL `"TRANSFER KEKURANGAN DANA UM ACARA BUKA PUASA..."` $\rightarrow$ WP `"UM ACARA BUKA PUASA..."` (Skor: 100%)

### Tahap 3: Keyword Anchor Matching (Penyelesaian Parsial Institusional)

Untuk transaksi yang memiliki variasi penamaan instansi/kontrak antara GL dan Working Paper (contoh: GL mencatat `"PENERIMAAN PEMBAYARAN PBB MSCM AJB JV 2"` senilai Rp 315.869.963 untuk melunasi pos `"PEMBAYARAN PBB JV 2 SUMMARECON TAHUN 2026"`):
- Sistem mencocokkan kata kunci unik (`PBB`, `JV`, `2`) yang hanya dimiliki oleh satu baris Working Paper.
- Diverifikasi dengan guard nominal (`KREDIT-IDR <= Sisa Saldo`) sehingga tercatat sebagai **Lunas Sebagian** dan menyisakan saldo gantung sebesar Rp 107.104.216 sesuai konteks soal.

### Multi-Voucher Settlement

Pada transaksi **Styling Apartemen The Parc**, pengajuan uang muka diselesaikan secara bertahap oleh banyak voucher GL. Sistem menerapkan **Pendekatan Single Row**:
- **Unit SM 1132 (2 Bedroom):** 8 voucher kredit GL digabungkan dengan koma (`ADV/BK/2604/0012, ..., PMT2/BM/2604/0007`), nominal dijumlahkan menjadi **Rp 25.695.900** (Saldo = Rp 0, Lunas Penuh).
- **Unit SM 1127 (Studio):** 3 voucher kredit GL digabungkan (`ADV/BK/2604/0019, 0020, PMT2/BM/2604/0008`), nominal dijumlahkan menjadi **Rp 1.583.700** (Saldo = Rp 0, Lunas Penuh).

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
