import os
from dotenv import load_dotenv
import pandas as pd

from modules.data_extractor import load_local_data
from modules.matcher import process_matching
from modules.ai_agent import generate_executive_summary
from modules.sheet_exporter import export_to_sheets

load_dotenv()

def main():
    print("="*50)
    print("Memulai Automasi SouthCity: Matching GL & Working Paper")
    print("="*50)

    gl_path = 'data/GL - Advances Other - April 2026.xls'
    wp_path = 'data/Working Paper Advances and Prepayment-Soal.xlsx'

    print("[1] Membaca dan membersihkan data dari file Excel...")
    try:
        gl_credit_df, wp_df = load_local_data(gl_path, wp_path)
        print(f" - Berhasil membaca {len(gl_credit_df)} baris transaksi Kredit dari GL.")
        print(f" - Berhasil membaca {len(wp_df)} baris transaksi di Working Paper.")
    except Exception as e:
        print(f" Gagal membaca file: {e}")
        return

    print("\n[2] Menjalankan Algoritma Matching (Regex & Fuzzy)...")
    try:
        result_df = process_matching(gl_credit_df, wp_df)
        
        settled_count = len(result_df[result_df['Realization Amount'] > 0])
        print(f" - Berhasil mencocokkan {settled_count} transaksi Advance.")
        
    except Exception as e:
        print(f"Gagal saat melakukan matching: {e}")
        return

    print("\n[3] Preview Data Hasil Matching:")
    
    display_cols = ['Deskripsi', 'Amount', 'Realization No Voucher', 'Realization Amount', 'Saldo']
    preview_data = result_df[display_cols].copy()
    
    pd.options.display.float_format = '{:,.0f}'.format
    
    print("\n Contoh Transaksi yang Berhasil Di-Settle")
    print(preview_data[preview_data['Realization Amount'] > 0].head(5).to_string(index=False))
    
    print("\n Contoh Transaksi yang Masih Gantung (Unsettled)")
    print(preview_data[preview_data['Saldo'] > 0].head(3).to_string(index=False))

    print("\n[4] Menghasilkan Executive Summary via AI...")
    try:
        summary_text = generate_executive_summary(result_df)
        print("\n" + "="*50)
        print(" EXECUTIVE SUMMARY (HASIL GEMINI AI)")
        print("="*50)
        print(summary_text)
        print("="*50)
    except Exception as e:
        print(f" Gagal memanggil AI: {e}")

    print("\n[5] Mengekspor Hasil ke Google Sheets...")
    try:
        export_to_sheets(result_df, summary_text)
    except Exception as e:
        print(f" Gagal mengekspor data: {e}")

    print("\n Seluruh proses automasi selesai! Silakan periksa Google Sheets Anda.")

if __name__ == "__main__":
    main()