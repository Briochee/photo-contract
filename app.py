"""Local Streamlit front end; all data stays on disk."""
from datetime import date
from pathlib import Path
import json
import streamlit as st
import pandas as pd
from core import DATA, list_records, next_references, save_record, totals, dollars, due_date
from render import export_pdfs

st.set_page_config(page_title='Photography · Documents', page_icon='▣', layout='wide')
st.markdown('''<style>
html,body,[class*="css"],.stApp{font-family:Calibri,Carlito,Arial,sans-serif!important}
.stApp{background:#f1f2ef;color:#24241f}h1,h2,h3{font-weight:500!important;letter-spacing:-.025em}.stButton button,.stDownloadButton button{border-radius:0!important;border:1px solid #24241f!important}.stButton button[kind="primary"]{background:#24241f;color:#fff}.stTextInput input,.stTextArea textarea,.stNumberInput input{border-radius:0!important}.eyebrow{color:#72283a;letter-spacing:.13em;font-size:12px;font-weight:bold;text-transform:uppercase}.muted{color:#66645d}.stDataFrame{border:1px solid #c9c9c5}
</style>''', unsafe_allow_html=True)

DEFAULT = {
    'photographer':'', 'photographer_address':'', 'photographer_email':'',
    'client':'', 'client_address':'', 'client_contact':'', 'client_email':'', 'client_phone':'',
    'agreement_date':date.today().isoformat(),'invoice_date':date.today().isoformat(),
    'event_name':'', 'event_date':date.today().isoformat(), 'venue':'',
    'start_time':'09:00','end_time':'15:00','coverage_hours':'6',
    'scope':'', 'image_count':'', 'delivery_deadline':'', 'delivery_method':'Online gallery',
    'special_deliverables':'','overtime_rate':'150','approved_expenses':'',
    'exceptions':'','net_days':15,'tax_amount':'0',
    'payment_instructions':'','invoice_notes':'',
    'booking_lines':[{'description':'Corporate event photography package (up to six hours; editing and delivery included)','quantity':'1','rate':'800'}],
    'invoice_extras':[],
}

def fresh():
    bk, inv = next_references()
    st.session_state.record = dict(DEFAULT, booking_ref=bk, invoice_ref=inv)

if 'record' not in st.session_state:
    fresh()

st.markdown('<div class="eyebrow">Local document studio / Photography</div>', unsafe_allow_html=True)
st.title('Bookings & invoices')
st.caption('Draft once. Generate a linked booking confirmation, invoice, and master agreement with Playwright. No cloud database or account required.')

with st.sidebar:
    st.subheader('Records')
    if st.button('＋ New booking', use_container_width=True):
        fresh(); st.rerun()
    choices = list_records()
    picked = st.selectbox('Open saved booking', ['Select saved record'] + [p.stem for p in choices])
    if st.button('Load selected', disabled=picked == 'Select saved record', use_container_width=True):
        st.session_state.record = json.loads((DATA / (picked + '.json')).read_text(encoding='utf-8'))
        st.rerun()
    st.divider()
    st.caption('All data is stored under ./data. PDF files are saved under ./data/exports/<booking reference>.')

r = st.session_state.record
st.info(f'Booking **{r["booking_ref"]}**  ↔  Invoice **{r["invoice_ref"]}**')

def field(key, label, **kwargs):
    r[key] = st.text_input(label, value=str(r.get(key,'')), key=f'{r["booking_ref"]}_{key}', **kwargs)

def area(key, label, **kwargs):
    r[key] = st.text_area(label, value=str(r.get(key,'')), key=f'{r["booking_ref"]}_{key}', **kwargs)

with st.expander('01 · Parties & master agreement', expanded=True):
    a,b=st.columns(2)
    with a:
        st.markdown('**Photographer**')
        field('photographer','Legal / business name');area('photographer_address','Address',height=70);field('photographer_email','Email')
    with b:
        st.markdown('**Client**')
        field('client','Client legal entity');area('client_address','Client address',height=70)
        field('client_contact','Authorized representative / title');field('client_email','Client email');field('client_phone','Client phone')
    field('agreement_date','Governing master agreement effective date (YYYY-MM-DD)')

with st.expander('02 · Assignment & deliverables', expanded=True):
    a,b=st.columns(2)
    with a:
        field('event_name','Event / assignment');field('event_date','Event date (YYYY-MM-DD)')
        area('venue','Venue / location',height=70);area('scope','Scope / photographic priorities',height=100)
    with b:
        field('start_time','Coverage begins');field('end_time','Coverage ends');field('coverage_hours','Included coverage hours')
        field('image_count','Guaranteed image count (blank if none)')
        field('delivery_deadline','Delivery deadline override (blank = 10 business days)')
        field('delivery_method','Delivery method')
    area('special_deliverables','Special deliverables (if any)',height=70)

with st.expander('03 · Agreed booking fees', expanded=True):
    st.caption('Items in this table appear on BOTH the booking confirmation and the invoice. Change these only before acceptance, or with mutual written agreement afterward.')
    df=pd.DataFrame(r['booking_lines'], columns=['description','quantity','rate'])
    df=st.data_editor(df, num_rows='dynamic', hide_index=True, use_container_width=True,
                      column_config={'description':st.column_config.TextColumn('Description',required=True),
                                     'quantity':st.column_config.TextColumn('Quantity'),
                                     'rate':st.column_config.TextColumn('Unit rate ($)')}, key=f'{r["booking_ref"]}_booking_editor')
    r['booking_lines']=df.fillna('').to_dict('records')
    a,b=st.columns(2)
    with a:
        field('overtime_rate','Agreed hourly overtime rate ($)');area('approved_expenses','Authorized expense categories / notes',height=70)
    with b:
        field('exceptions','Exceptions to master agreement (specific clause + replacement, or None)')
    st.warning('The booking confirmation is a legally significant acceptance record. Do not retroactively change agreed fees without both parties accepting the change.')

with st.expander('04 · Invoice-only approved additions', expanded=True):
    st.caption('These appear ONLY on the invoice. Confirm advance written client authorization for every addition; the invoice must not silently change the accepted booking.')
    extras=pd.DataFrame(r['invoice_extras'],columns=['description','quantity','rate','approved'])
    extras=st.data_editor(extras, num_rows='dynamic', hide_index=True, use_container_width=True,
        column_config={'description':st.column_config.TextColumn('Approved cost / fee'),
            'quantity':st.column_config.TextColumn('Qty'), 'rate':st.column_config.TextColumn('Rate ($)'),
            'approved':st.column_config.CheckboxColumn('Written approval confirmed',default=False)},
        key=f'{r["booking_ref"]}_extra_editor')
    r['invoice_extras']=extras.fillna({'description':'','quantity':'','rate':'','approved':False}).to_dict('records')
    a,b=st.columns(2)
    with a:
        field('invoice_date','Invoice date (YYYY-MM-DD)')
        r['net_days']=st.number_input('Payment term (days)', min_value=0,max_value=365,value=int(r['net_days']),key=f'{r["booking_ref"]}_net_days')
        field('tax_amount','Tax amount ($), manually verified')
    with b:
        area('payment_instructions','Payment instructions',height=100)
        area('invoice_notes','Invoice notes',height=85)
    st.caption('Sales tax is not calculated automatically; verify whether and how it applies to your specific services and deliverables.')

try:
    calc=totals(r['booking_lines'],r['invoice_extras'],r['tax_amount'])
    date.fromisoformat(r['invoice_date']);date.fromisoformat(r['agreement_date']);date.fromisoformat(r['event_date'])
    error=None
except (ValueError,TypeError) as e:
    calc=None;error=str(e)
if error:
    st.error('Please correct the details: ' + error)
else:
    st.divider()
    a,b,c=st.columns(3)
    a.metric('Booking fees',dollars(calc['booking_subtotal']))
    b.metric('Approved invoice additions',dollars(calc['extra_subtotal']))
    c.metric('Invoice total',dollars(calc['grand_total']))
    st.caption('Invoice due: '+due_date(r['invoice_date'],r['net_days']))

left,right=st.columns([1,2])
with left:
    if st.button('Save record',disabled=bool(error),use_container_width=True):
        save_record(r);st.success('Saved locally.')
with right:
    if st.button('Generate 3 PDFs with Playwright',type='primary',disabled=bool(error),use_container_width=True):
        try:
            save_record(r)
            dest=DATA/'exports'/r['booking_ref']
            pdfs=export_pdfs(r,dest)
            st.session_state['exports']= {k:str(v) for k,v in pdfs.items()}
            st.success('PDFs generated and saved locally.')
        except Exception as exc:
            st.error(f'PDF generation failed: {exc}. Run: python -m playwright install chromium')

if st.session_state.get('exports'):
    st.subheader('Documents')
    for kind,path in st.session_state['exports'].items():
        path=Path(path)
        if path.exists() and r['booking_ref'] in str(path):
            st.download_button(f'Download {kind.title()} PDF',path.read_bytes(),file_name=path.name,mime='application/pdf',key=f'dl_{kind}')

st.caption('Draft documents for review, not legal or tax advice. Confirm legal names, authorization, taxes, and written approvals before sending.')
