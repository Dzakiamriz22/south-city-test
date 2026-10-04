import os
import pandas as pd
from dotenv import load_dotenv

from modules.data_extractor import load_local_data
from modules.matcher import process_matching
from modules.summary import compute_summary, format_rupiah
from modules.ai_agent import generate_executive_summary
from modules.sheet_exporter import export_to_sheets

load_dotenv()

def main():
    print("=" * 50)
    print("Automasi SouthCity: Matching GL & Working Paper")
    print("=" * 50)

    gl_path = 'data/GL - Advances Other - April 2026.xls'
    wp_path = 'data/Working Paper Advances and Prepayment-Soal.xlsx'

    print("[1] Membaca data Excel...")
    try:
        gl_credit_df, wp_df = load_local_data(gl_path, wp_path)
        print(f" - GL Kredit: {len(gl_credit_df)} baris")
        print(f" - Working Paper: {len(wp_df)} baris")
    except Exception as e:
        print(f"Gagal membaca file: {e}")
        return

    print("\n[2] Menjalankan matching...")
    try:
        result_df = process_matching(gl_credit_df, wp_df)
        summary = compute_summary(result_df, len(gl_credit_df))
        print(f" - Realisasi terbukukan: {format_rupiah(summary['total_realized'])} ({summary['settlement_rate']*100:.1f}%)")
        print(f" - Sisa saldo unsettled: {format_rupiah(summary['unsettled'])}")
    except Exception as e:
        print(f"Gagal saat matching: {e}")
        return

    print("\n[3] Preview:")
    display_cols = ['Deskripsi', 'Amount', 'Realization No Voucher', 'Realization Amount', 'Saldo']
    preview_data = result_df[display_cols].copy()
    pd.options.display.float_format = '{:,.0f}'.format
    
    print("\n- Transaksi Lunas:")
    print(preview_data[preview_data['Saldo'] == 0].head(4).to_string(index=False))
    
    print("\n- Transaksi Sisa Saldo:")
    print(preview_data[preview_data['Saldo'] > 0].to_string(index=False))

    print("\n- Transaksi Over-settled:")
    print(preview_data[preview_data['Saldo'] < 0].to_string(index=False))

    print("\n[4] Menghasilkan Executive Summary...")
    try:
        summary_text = generate_executive_summary(result_df, summary=summary)
        print("\n" + "=" * 50)
        print(summary_text)
        print("=" * 50)
    except Exception as e:
        print(f"Gagal memanggil AI: {e}")
        summary_text = ""

    print("\n[5] Ekspor ke Google Sheets...")
    try:
        export_to_sheets(result_df, summary_text)
    except Exception as e:
        print(f"Gagal ekspor: {e}")

if __name__ == "__main__":
    main()