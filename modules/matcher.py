import pandas as pd
import re
from rapidfuzz import process, fuzz

def extract_po_number(text):
    match = re.search(r'[A-Z0-9]+/[A-Z0-9]+/\d+', text)
    return match.group(0) if match else None

def process_matching(gl_df, wp_df):
    gl_df['PO_Number'] = gl_df['DESKRIPSI'].apply(extract_po_number)
    wp_df['PO_Number'] = wp_df['Deskripsi'].apply(extract_po_number)
    
    settlement_data = {}
    
    for index, gl_row in gl_df.iterrows():
        gl_desc = gl_row['DESKRIPSI']
        gl_po = gl_row['PO_Number']
        matched_wp_index = None
        
        if pd.notna(gl_po):
            match_candidates = wp_df[wp_df['PO_Number'] == gl_po]
            if not match_candidates.empty:
                matched_wp_index = match_candidates.index[0]
                
        else:
            wp_descriptions = wp_df['Deskripsi'].to_dict()
            result = process.extractOne(
                gl_desc, 
                wp_descriptions, 
                scorer=fuzz.token_set_ratio, 
                score_cutoff=85
            )
            if result:
                matched_wp_index = result[2]
                
        if matched_wp_index is not None:
            if matched_wp_index not in settlement_data:
                settlement_data[matched_wp_index] = {
                    'dates': [str(gl_row['TANGGAL']).split()[0]], 
                    'vouchers': [gl_row['NO JURNAL']],
                    'total_amount': gl_row['KREDIT-IDR']
                }
            else:
                settlement_data[matched_wp_index]['dates'].append(str(gl_row['TANGGAL']).split()[0])
                settlement_data[matched_wp_index]['vouchers'].append(gl_row['NO JURNAL'])
                settlement_data[matched_wp_index]['total_amount'] += gl_row['KREDIT-IDR']

    for wp_idx, data in settlement_data.items():
        wp_df.at[wp_idx, 'Realization Date'] = ", ".join(sorted(set(data['dates'])))
        wp_df.at[wp_idx, 'Realization No Voucher'] = ", ".join(data['vouchers'])
        wp_df.at[wp_idx, 'Realization Amount'] = data['total_amount']
        
    wp_df['Realization Amount'] = pd.to_numeric(wp_df['Realization Amount'], errors='coerce').fillna(0)
    wp_df['Saldo'] = wp_df['Amount'] - wp_df['Realization Amount']
    
    return wp_df