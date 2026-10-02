import pandas as pd

def load_local_data(gl_path, wp_path):
    gl_df = pd.read_excel(gl_path)
    gl_credit_df = gl_df[gl_df['KREDIT-IDR'] > 0].copy()

    gl_credit_df['DESKRIPSI'] = gl_credit_df['DESKRIPSI'].astype(str).str.strip().str.upper()
    gl_credit_df['NO_JURNAL'] = gl_credit_df['NO JURNAL'].astype(str).str.strip()

    wp_df = pd.read_excel(wp_path, skiprows=4)

    wp_df.rename(columns={
            'Unnamed: 0': 'Date',
            'Unnamed: 1': 'Voucher No Awal',
            'Unnamed: 2': 'Deskripsi',
            'Unnamed: 3': 'Amount',
            'Unnamed: 4': 'Realization Date',
            'Unnamed: 5': 'Realization No Voucher',
            'Unnamed: 6': 'Realization Amount',
            'Unnamed: 7': 'Saldo'
        }, inplace=True)

    wp_df['Amount'] = pd.to_numeric(wp_df['Amount'], errors='coerce')
    wp_df = wp_df[wp_df['Amount'].notna()].copy()
    wp_df['Deskripsi'] = wp_df['Deskripsi'].astype(str).str.strip().str.upper()
    wp_df['Date'] = pd.to_datetime(wp_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
    wp_df = wp_df.loc[:, ~wp_df.columns.str.startswith('Unnamed')].copy()

    return gl_credit_df, wp_df