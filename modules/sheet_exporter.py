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

load_dotenv()

def export_to_sheets(result_df, summary_text):
    creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "credentials.json")
    sheet_id = os.getenv("SPREADSHEET_ID")
    
    if not sheet_id:
        print(" SPREADSHEET_ID tidak ditemukan di .env")
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
            
        export_df = result_df.copy().fillna("")
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
        format_cell_range(ws_result, 'A1:I1', fmt_header)
        
        fmt_currency = cellFormat(
            numberFormat=numberFormat(type='CURRENCY', pattern='[$Rp-id-ID] #,##0')
        )
        format_cell_range(ws_result, 'D2:D100', fmt_currency)
        format_cell_range(ws_result, 'G2:H100', fmt_currency)
        
        set_column_width(ws_result, 'C', 450)
        set_column_width(ws_result, 'D', 150)
        set_column_width(ws_result, 'F', 200)
        set_column_width(ws_result, 'G', 150)
        set_column_width(ws_result, 'H', 150)
        
        ws_result.freeze(rows=1)
        
        print(" Data tabular berhasil diekspor & distyling di 'Working_Paper_Result'")
        
        try:
            ws_dashboard = spreadsheet.worksheet("Dashboard")
            ws_dashboard.clear()
        except gspread.exceptions.WorksheetNotFound:
            ws_dashboard = spreadsheet.add_worksheet(title="Dashboard", rows="200", cols="5")

        # === KONTROL PANEL (KPI Metrics) ===
        total_advance = result_df['Amount'].sum()
        total_settled = result_df['Realization Amount'].sum()
        total_unsettled = total_advance - total_settled
        settled_count = len(result_df[result_df['Realization Amount'] > 0])
        unsettled_count = len(result_df[result_df['Saldo'] > 0])
        settlement_rate = (total_settled / total_advance * 100) if total_advance > 0 else 0

        ws_dashboard.update_acell('A1', " KONTROL PANEL - ADVANCE SETTLEMENT APRIL 2026")

        control_panel = [
            ["Metrik", "Nilai"],
            ["Total Advance Awal", f"Rp {total_advance:,.0f}"],
            ["Total Realisasi (Settled)", f"Rp {total_settled:,.0f}"],
            ["Total Saldo Unsettled", f"Rp {total_unsettled:,.0f}"],
            ["Settlement Rate", f"{settlement_rate:.1f}%"],
            ["Jumlah Transaksi Settled", settled_count],
            ["Jumlah Transaksi Unsettled", unsettled_count],
            ["Total Transaksi Working Paper", len(result_df)],
        ]
        ws_dashboard.update(range_name='A2', values=control_panel)

        format_cell_range(ws_dashboard, 'A1:B1', cellFormat(
            backgroundColor=color(0.1, 0.3, 0.6),
            textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1), fontSize=14)
        ))
        format_cell_range(ws_dashboard, 'A2:B2', cellFormat(
            backgroundColor=color(0.85, 0.85, 0.85),
            textFormat=textFormat(bold=True)
        ))
        format_cell_range(ws_dashboard, 'A3:A9', cellFormat(
            textFormat=textFormat(bold=True)
        ))

        set_column_width(ws_dashboard, 'A', 350)
        set_column_width(ws_dashboard, 'B', 250)

        summary_start_row = 11
        ws_dashboard.update_acell(f'A{summary_start_row}', " EXECUTIVE SUMMARY (AI-Generated)")
        format_cell_range(ws_dashboard, f'A{summary_start_row}', cellFormat(
            backgroundColor=color(0.2, 0.7, 0.5),
            textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1), fontSize=13)
        ))

        summary_lines = summary_text.split('\n')
        dashboard_data = [[line] for line in summary_lines]
        ws_dashboard.update(range_name=f'A{summary_start_row + 1}', values=dashboard_data)

        for i, line in enumerate(summary_lines):
            row_idx = summary_start_row + 1 + i
            if line.isupper() and len(line.strip()) > 3:
                format_cell_range(ws_dashboard, f'A{row_idx}', cellFormat(textFormat=textFormat(bold=True)))
                
        print(" Kontrol Panel & Executive Summary AI berhasil diekspor di 'Dashboard'")
        print(f"\n Link Spreadsheet Anda: https://docs.google.com/spreadsheets/d/{sheet_id}/edit")
        
    except Exception as e:
        print(f" Terjadi kesalahan saat mengekspor ke Google Sheets: {e}")