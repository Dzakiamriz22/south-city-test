import os
from google import genai
import pandas as pd
import time

def generate_executive_summary(wp_df):
    """
    Menganalisis hasil rekonsiliasi dan membuat Executive Summary menggunakan Gemini API.
    Menggunakan SDK terbaru 'google-genai' dengan arsitektur failover ringan.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "ERROR: GEMINI_API_KEY tidak ditemukan di file .env."
    
    total_advance = wp_df['Amount'].sum()
    total_settled = wp_df['Realization Amount'].sum()
    total_unsettled_balance = total_advance - total_settled
    
    unsettled_df = wp_df[wp_df['Saldo'] > 0][['Deskripsi', 'Amount', 'Saldo']]
    unsettled_text = unsettled_df.to_string(index=False)
    
    prompt = f"""
    Anda adalah seorang AI Financial Analyst di SouthCity.
    Tugas Anda adalah membuat 'Executive Summary' untuk proses settlement Uang Muka (Advances) bulan April 2026.
    
    DATA RINGKASAN:
    - Total Advance Awal: Rp {total_advance:,.0f}
    - Total Realisasi (Settled): Rp {total_settled:,.0f}
    - Sisa Saldo Keseluruhan: Rp {total_unsettled_balance:,.0f}
    
    DAFTAR TRANSAKSI UNSETTLED (Masih Gantung):
    {unsettled_text}
    
    INSTRUKSI OUTPUT:
    1. Ringkasan Eksekutif: Jelaskan performa settlement berdasarkan angka agregasi di atas.
    2. Rincian Unsettled: Soroti item Advance yang masih memiliki sisa saldo. Berikan perhatian khusus pada transaksi besar (seperti PBB JV 2 Summarecon jika ada di data).
    3. Saran Tindak Lanjut: Berikan rekomendasi aksi konkret untuk tim Finance (contoh: menagih faktur, mengecek kelengkapan dokumen vendor, dll).
    
    Gunakan format Plain Text (TANPA Markdown, JANGAN gunakan simbol bintang ** untuk bold, JANGAN gunakan hashtag # untuk heading). Gunakan penomoran standar dan bahasa Indonesia yang profesional, ringkas, dan langsung pada intinya.
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
                return response.text
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return f"GAGAL: Terjadi kesalahan API setelah {max_retries} percobaan. Error: {str(e)}"
                
    except Exception as init_err:
        return f"GAGAL Inisialisasi Client AI: {str(init_err)}"