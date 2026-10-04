import pandas as pd
import re
from rapidfuzz import process, fuzz

PO_PATTERN = re.compile(r'\b[A-Z][A-Z0-9]*/(?:PO|WO)/\d+\b')
FUZZY_CUTOFF = 85
MIN_ANCHOR_TOKENS = 2

MONTHS = ['JANUARI', 'FEBRUARI', 'MARET', 'APRIL', 'MEI', 'JUNI', 'JULI',
          'AGUSTUS', 'SEPTEMBER', 'OKTOBER', 'NOVEMBER', 'DESEMBER']

STOPWORDS = {'PELUNASAN', 'PENGEMBALIAN', 'KELEBIHAN', 'KEKURANGAN', 'DANA', 'UM',
             'TRANSFER', 'PENERIMAAN', 'PEMBAYARAN', 'ADVANCE', 'UNTUK'}


def extract_po_number(text):
    match = PO_PATTERN.search(str(text))
    return match.group(0) if match else None


def normalize_text(text):
    text = re.sub(r'\([^)]*\)', ' ', str(text))
    text = PO_PATTERN.sub(' ', text)
    return ' '.join(t for t in text.split() if t not in STOPWORDS)


def months_conflict(text_a, text_b):
    a = {m for m in MONTHS if m in text_a}
    b = {m for m in MONTHS if m in text_b}
    return bool(a and b and not (a & b))


def build_anchor_tokens(wp_pool):
    tokens_per_row = {
        idx: {t for t in normalize_text(desc).split()
              if t.isalpha() and len(t) >= 2 and t not in MONTHS}
        for idx, desc in wp_pool['Deskripsi'].items()
    }
    doc_freq = {}
    for tokens in tokens_per_row.values():
        for t in tokens:
            doc_freq[t] = doc_freq.get(t, 0) + 1
    return {idx: {t for t in tokens if doc_freq[t] == 1}
            for idx, tokens in tokens_per_row.items()}


def process_matching(gl_df, wp_df):
    gl_df['PO_Number'] = gl_df['DESKRIPSI'].apply(extract_po_number)
    wp_df['PO_Number'] = wp_df['Deskripsi'].apply(extract_po_number)
    wp_df['Match_Method'] = ''

    settlement_data = {}
    unmatched_gl = []

    text_pool = wp_df[wp_df['PO_Number'].isna()]
    fuzzy_choices = {idx: normalize_text(desc) for idx, desc in text_pool['Deskripsi'].items()}

    def remaining_saldo(wp_idx):
        realized = settlement_data.get(wp_idx, {}).get('total_amount', 0)
        return wp_df.at[wp_idx, 'Amount'] - realized

    def record(wp_idx, gl_row, method):
        if wp_idx not in settlement_data:
            settlement_data[wp_idx] = {
                'dates': [str(gl_row['TANGGAL']).split()[0]],
                'vouchers': [gl_row['NO JURNAL']],
                'total_amount': gl_row['KREDIT-IDR'],
                'methods': {method},
            }
        else:
            settlement_data[wp_idx]['dates'].append(str(gl_row['TANGGAL']).split()[0])
            settlement_data[wp_idx]['vouchers'].append(gl_row['NO JURNAL'])
            settlement_data[wp_idx]['total_amount'] += gl_row['KREDIT-IDR']
            settlement_data[wp_idx]['methods'].add(method)

    for _, gl_row in gl_df.iterrows():
        gl_desc = gl_row['DESKRIPSI']
        gl_po = gl_row['PO_Number']
        gl_amount = gl_row['KREDIT-IDR']

        if pd.notna(gl_po):
            candidates = wp_df[wp_df['PO_Number'] == gl_po]
            if not candidates.empty:
                record(candidates.index[0], gl_row, 'PO')
                continue

        result = process.extractOne(
            normalize_text(gl_desc),
            fuzzy_choices,
            scorer=fuzz.token_set_ratio,
            score_cutoff=FUZZY_CUTOFF
        )
        if result:
            wp_idx = result[2]
            same_period = not months_conflict(gl_desc, wp_df.at[wp_idx, 'Deskripsi'])
            within_saldo = gl_amount <= remaining_saldo(wp_idx)
            if same_period and within_saldo:
                record(wp_idx, gl_row, 'Fuzzy')
                continue

        unmatched_gl.append(gl_row)

    anchors = build_anchor_tokens(text_pool)
    for gl_row in unmatched_gl:
        gl_tokens = set(normalize_text(gl_row['DESKRIPSI']).split())
        candidates = [
            idx for idx, tokens in anchors.items()
            if len(gl_tokens & tokens) >= MIN_ANCHOR_TOKENS
            and not months_conflict(gl_row['DESKRIPSI'], wp_df.at[idx, 'Deskripsi'])
            and gl_row['KREDIT-IDR'] <= remaining_saldo(idx)
        ]
        if len(candidates) == 1:
            record(candidates[0], gl_row, 'Keyword')

    for wp_idx, data in settlement_data.items():
        wp_df.at[wp_idx, 'Realization Date'] = ", ".join(sorted(set(data['dates'])))
        wp_df.at[wp_idx, 'Realization No Voucher'] = ", ".join(data['vouchers'])
        wp_df.at[wp_idx, 'Realization Amount'] = data['total_amount']
        wp_df.at[wp_idx, 'Match_Method'] = " + ".join(sorted(data['methods']))
        
    wp_df['Realization Amount'] = pd.to_numeric(wp_df['Realization Amount'], errors='coerce').fillna(0)
    wp_df['Saldo'] = wp_df['Amount'] - wp_df['Realization Amount']
    
    return wp_df