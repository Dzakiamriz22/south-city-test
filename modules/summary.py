import pandas as pd

STATUS_LUNAS = 'Lunas'
STATUS_SEBAGIAN = 'Lunas Sebagian'
STATUS_BELUM = 'Belum Ada Realisasi'
STATUS_OVER = 'Over-settled'


def format_rupiah(value):
    sign = '-' if value < 0 else ''
    return f"{sign}Rp {abs(value):,.0f}".replace(',', '.')


def classify_status(row):
    if row['Saldo'] < 0:
        return STATUS_OVER
    if row['Realization Amount'] == 0:
        return STATUS_BELUM
    if row['Saldo'] > 0:
        return STATUS_SEBAGIAN
    return STATUS_LUNAS


def compute_summary(result_df, gl_credit_count=None):
    df = result_df.copy()
    df['Status'] = df.apply(classify_status, axis=1)

    total_advance = df['Amount'].sum()
    total_realized = df['Realization Amount'].sum()
    unsettled = df.loc[df['Saldo'] > 0, 'Saldo'].sum()
    over_settled = -df.loc[df['Saldo'] < 0, 'Saldo'].sum()

    settlement_rate = (total_advance - unsettled) / total_advance if total_advance else 0

    matched_vouchers = sum(
        len([v for v in str(x).split(',') if v.strip()])
        for x in df['Realization No Voucher'].dropna()
    )

    status_counts = df['Status'].value_counts()
    follow_up = df[df['Status'] != STATUS_LUNAS]

    return {
        'total_advance': total_advance,
        'total_realized': total_realized,
        'unsettled': unsettled,
        'over_settled': over_settled,
        'settlement_rate': settlement_rate,
        'item_count': len(df),
        'count_lunas': int(status_counts.get(STATUS_LUNAS, 0)),
        'count_sebagian': int(status_counts.get(STATUS_SEBAGIAN, 0)),
        'count_belum': int(status_counts.get(STATUS_BELUM, 0)),
        'count_over': int(status_counts.get(STATUS_OVER, 0)),
        'matched_vouchers': matched_vouchers,
        'gl_credit_count': gl_credit_count,
        'follow_up': follow_up[['Deskripsi', 'Amount', 'Realization Date',
                                'Realization No Voucher', 'Realization Amount',
                                'Saldo', 'Status']],
    }
