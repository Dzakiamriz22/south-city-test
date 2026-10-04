import os
import time
from google import genai
from modules.summary import compute_summary, format_rupiah

def generate_executive_summary(wp_df, summary=None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "ERROR: GEMINI_API_KEY tidak ditemukan di file .env."

    if summary is None:
        summary = compute_summary(wp_df)

    follow_up_rows = []
    for _, row in summary['follow_up'].iterrows():
        deskripsi = row['Deskripsi']
        amount = format_rupiah(row['Amount'])
        realisasi = format_rupiah(row['Realization Amount'])
        saldo = format_rupiah(row['Saldo'])
        status = row['Status']
        follow_up_rows.append(
            f"- {deskripsi}\n  Status: {status} | Pengajuan: {amount} | Realisasi: {realisasi} | Saldo: {saldo}"
        )
    follow_up_text = "\n".join(follow_up_rows)

    prompt = f"""
Anda adalah AI Financial Analyst di SouthCity.
Buatkan Executive Summary singkat, profesional, dan padat untuk proses settlement Uang Muka (Advances) periode April 2026.

DATA REKONSILIASI KEUANGAN:
- Total Advance Awal: {format_rupiah(summary['total_advance'])} ({summary['item_count']} transaksi)
- Total Realisasi (Settled): {format_rupiah(summary['total_realized'])}
- Sisa Saldo Unsettled (Belum Selesai): {format_rupiah(summary['unsettled'])}
- Kelebihan Realisasi (Over-settled): {format_rupiah(summary['over_settled'])}
- Tingkat Penyelesaian (Settlement Rate): {summary['settlement_rate']*100:.1f}%
- Rincian Status Transaksi:
  * {summary['count_lunas']} transaksi LUNAS PENUH (termasuk multi-voucher Styling Apartemen)
  * {summary['count_sebagian']} transaksi LUNAS SEBAGIAN (PBB JV 2 Summarecon terealisasi {format_rupiah(315869963)} dari pengajuan {format_rupiah(422974179)}, menyisakan saldo {format_rupiah(107104216)})
  * {summary['count_over']} transaksi OVER-SETTLED (Lemari Kids Room pengajuan 50% {format_rupiah(3300000)} tetapi direalisasikan 100% {format_rupiah(6600000)}, saldo -{format_rupiah(3300000)})

TRANSAKSI YANG MEMERLUKAN PERHATIAN:
{follow_up_text}

INSTRUKSI FORMAT & GAYA BAHASA:
1. Format Plain Text SAJA (DILARANG menggunakan simbol markdown bintang ** untuk bold, DILARANG menggunakan tanda pagar #).
2. DILARANG membuat header memo fiktif seperti 'MEMORANDUM INTERNAL', 'Kepada:', 'Dari:', atau mengarang tanggal spesifik.
3. Tulis dengan singkat, padat, lugas, dan berbobot dalam Bahasa Indonesia formal akuntansi.
4. Susun dalam 3 bagian terstruktur:
   1. RINGKASAN EKSEKUTIF: Ulas performa settlement (tingkat penyelesaian {summary['settlement_rate']*100:.1f}%, mayoritas transaksi lunas).
   2. RINCIAN ITEM BERMASALAH: Soroti transaksi PBB JV 2 Summarecon yang masih bersaldo {format_rupiah(summary['unsettled'])} dan over-settlement Lemari Kids Room.
   3. SARAN TINDAK LANJUT: Rekomendasi aksi nyata untuk tim Finance (verifikasi dokumen SSPD PBB ke pihak JV Summarecon dan konfirmasi selisih tagihan vendor Lemari).
"""

    try:
        client = genai.Client(api_key=api_key)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=prompt
                )
                return response.text.strip()
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return f"GAGAL: Terjadi kesalahan API setelah {max_retries} percobaan. Error: {str(e)}"

    except Exception as init_err:
        return f"GAGAL Inisialisasi Client AI: {str(init_err)}"