import os
import gspread
from gspread_formatting import (
    cellFormat,
    color,
    textFormat,
    numberFormat,
    format_cell_range,
    set_column_width,
)
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from dotenv import load_dotenv
from modules.summary import compute_summary, format_rupiah

load_dotenv()

def export_to_sheets(result_df, summary_text):
    creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "credentials.json")
    sheet_id = os.getenv("SPREADSHEET_ID")
    
    if not sheet_id:
        print("SPREADSHEET_ID tidak ditemukan di .env")
        return

    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(sheet_id)

        try:
            ws_result = spreadsheet.worksheet("Working_Paper_Result")
            ws_result.clear() 
        except gspread.exceptions.WorksheetNotFound:
            ws_result = spreadsheet.add_worksheet(title="Working_Paper_Result", rows="100", cols="20")
            
        target_columns = [
            'Date', 'Voucher No Awal', 'Deskripsi', 'Amount',
            'Realization Date', 'Realization No Voucher', 'Realization Amount', 'Saldo'
        ]
        available_cols = [c for c in target_columns if c in result_df.columns]
        export_df = result_df[available_cols].copy().fillna("")
        
        for col in export_df.columns:
            if pd.api.types.is_datetime64_any_dtype(export_df[col]):
                export_df[col] = export_df[col].astype(str)
                
        data_to_write = [export_df.columns.values.tolist()] + export_df.values.tolist()
        ws_result.update(range_name='A1', values=data_to_write)

        fmt_header = cellFormat(
            backgroundColor=color(0.1, 0.3, 0.6),
            textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1)),
            horizontalAlignment='CENTER'
        )
        format_cell_range(ws_result, 'A1:H1', fmt_header)
        
        fmt_currency = cellFormat(
            numberFormat=numberFormat(type='CURRENCY', pattern='[$Rp-id-ID] #,##0')
        )
        format_cell_range(ws_result, 'D2:D100', fmt_currency)
        format_cell_range(ws_result, 'G2:H100', fmt_currency)
        
        set_column_width(ws_result, 'A', 110)
        set_column_width(ws_result, 'B', 170)
        set_column_width(ws_result, 'C', 450)
        set_column_width(ws_result, 'D', 140)
        set_column_width(ws_result, 'E', 140)
        set_column_width(ws_result, 'F', 260)
        set_column_width(ws_result, 'G', 150)
        set_column_width(ws_result, 'H', 150)
        
        ws_result.freeze(rows=1)
        print("Data tabular berhasil diekspor di 'Working_Paper_Result'")
        
        try:
            ws_dashboard = spreadsheet.worksheet("Dashboard")
            ws_dashboard.clear()
        except gspread.exceptions.WorksheetNotFound:
            ws_dashboard = spreadsheet.add_worksheet(title="Dashboard", rows="200", cols="5")

        summary = compute_summary(result_df)

        ws_dashboard.update_acell('A1', "KONTROL PANEL - ADVANCE SETTLEMENT APRIL 2026")

        control_panel = [
            ["Metrik", "Nilai"],
            ["Total Advance Awal", format_rupiah(summary['total_advance'])],
            ["Total Realisasi (Settled)", format_rupiah(summary['total_realized'])],
            ["Total Saldo Unsettled (Outstanding)", format_rupiah(summary['unsettled'])],
            ["Kelebihan Realisasi (Over-settled)", format_rupiah(summary['over_settled'])],
            ["Tingkat Penyelesaian (Settlement Rate)", f"{summary['settlement_rate']*100:.1f}%"],
            ["Transaksi Lunas Penuh", summary['count_lunas']],
            ["Transaksi Lunas Sebagian", summary['count_sebagian']],
            ["Transaksi Over-settled", summary['count_over']],
            ["Total Item Working Paper", summary['item_count']],
            ["Voucher Kredit GL Terpadankan", summary['matched_vouchers']],
        ]
        ws_dashboard.update(range_name='A2', values=control_panel)

        format_cell_range(ws_dashboard, 'A1:B1', cellFormat(
            backgroundColor=color(0.1, 0.3, 0.6),
            textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1), fontSize=13)
        ))
        format_cell_range(ws_dashboard, 'A2:B2', cellFormat(
            backgroundColor=color(0.85, 0.85, 0.85),
            textFormat=textFormat(bold=True)
        ))
        format_cell_range(ws_dashboard, 'A3:A12', cellFormat(
            textFormat=textFormat(bold=True)
        ))

        set_column_width(ws_dashboard, 'A', 340)
        set_column_width(ws_dashboard, 'B', 220)

        summary_start_row = 14
        ws_dashboard.update_acell(f'A{summary_start_row}', "EXECUTIVE SUMMARY (AI-Generated)")
        format_cell_range(ws_dashboard, f'A{summary_start_row}:B{summary_start_row}', cellFormat(
            backgroundColor=color(0.2, 0.7, 0.5),
            textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1), fontSize=12)
        ))

        summary_lines = summary_text.split('\n')
        dashboard_data = [[line] for line in summary_lines]
        ws_dashboard.update(range_name=f'A{summary_start_row + 1}', values=dashboard_data)

        for i, line in enumerate(summary_lines):
            row_idx = summary_start_row + 1 + i
            trimmed = line.strip()
            if (trimmed.isupper() and len(trimmed) > 3) or (len(trimmed) > 2 and trimmed[:2] in ['1.', '2.', '3.']):
                format_cell_range(ws_dashboard, f'A{row_idx}', cellFormat(textFormat=textFormat(bold=True)))
                
        print("Kontrol Panel & Executive Summary AI berhasil diekspor di 'Dashboard'")
        print(f"\nLink Spreadsheet: https://docs.google.com/spreadsheets/d/{sheet_id}/edit")
        
    except Exception as e:
        print(f"Gagal saat ekspor ke Google Sheets: {e}")