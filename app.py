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
:root {
  --paper: #f1f2ef;
  --paper-deep: #dfe4e2;
  --surface: #f8f9f5;
  --surface-raised: #fdfdf9;
  --surface-muted: #e8e8e2;
  --nav-surface: #e7e8e4;
  --ink: #24241f;
  --ink-soft: #66645d;
  --line: rgba(36, 36, 31, 0.18);
  --line-strong: rgba(36, 36, 31, 0.5);
  --accent: #72283a;
  --accent-wash: #f0e5e4;
  --focus: #2458a6;
}

* { box-sizing: border-box; }
html, body, [class*="css"], .stApp {
  font-family: Calibri, Carlito, Arial, sans-serif !important;
  color: var(--ink);
}
.stApp, [data-testid="stAppViewContainer"] { background: var(--paper); }
[data-testid="stHeader"] { background: transparent; }
main .block-container {
  max-width: 1320px;
  padding: clamp(1.75rem, 4vw, 3.5rem) clamp(1.25rem, 4.2vw, 4rem) 5rem;
}
section[data-testid="stSidebar"] {
  background: var(--nav-surface);
  border-right: 1px solid var(--line-strong);
}
section[data-testid="stSidebar"] > div { padding-top: 1.5rem; }
h1, h2, h3 { color: var(--ink) !important; font-weight: 500 !important; letter-spacing: -0.035em; }
p { color: var(--ink); }
hr { border-color: var(--line-strong); }

.studio-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(230px, 270px);
  align-items: end;
  gap: clamp(1.5rem, 4vw, 3.5rem);
  margin: 0 6px 2rem 0;
  padding: 0 0 1.75rem;
  border-bottom: 2px solid var(--ink);
  position: relative;
}
.studio-hero::after {
  content: "";
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 5rem;
  height: 5px;
  background: var(--accent);
}
.eyebrow, .studio-index__label {
  color: var(--accent);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.studio-hero h1 {
  margin: 0.35rem 0 1rem !important;
  font-size: clamp(3rem, 6vw, 5.6rem) !important;
  line-height: 0.94;
}
.studio-hero h1 span { color: var(--accent); }
.studio-hero__copy p {
  max-width: 60ch;
  margin: 0;
  color: var(--ink-soft);
  font-size: 1rem;
  line-height: 1.6;
}
.studio-index {
  margin: 0 6px 6px 0;
  padding: 1rem 1.1rem 0.8rem;
  border: 1px solid var(--ink);
  background: var(--surface);
  box-shadow: 6px 6px 0 var(--accent);
}
.studio-index ol { list-style: none; margin: 0.55rem 0 0; padding: 0; }
.studio-index li {
  display: flex;
  align-items: baseline;
  gap: 0.8rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid var(--line);
  color: var(--ink);
  font-size: 0.86rem;
}
.studio-index li:last-child { border-bottom: 0; }
.studio-index li span { color: var(--accent); font-size: 0.68rem; font-weight: 700; letter-spacing: 0.08em; }
.studio-index li strong { font-weight: 600; }

[data-testid="stWidgetLabel"] p {
  color: var(--ink-soft);
  font-size: 0.76rem;
  font-weight: 600;
  letter-spacing: 0.035em;
}
div[data-testid="stExpander"] details {
  border: 1px solid var(--line-strong) !important;
  border-radius: 0 !important;
  background: var(--surface);
}
div[data-testid="stExpander"] details > summary {
  border-left: 4px solid var(--accent);
  padding: 0.8rem 1rem;
}
div[data-testid="stExpander"] details[open] > summary { border-bottom: 1px solid var(--line); }
div[data-testid="stExpander"] details > summary p { font-weight: 600; }

input, textarea,
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div {
  border-radius: 0 !important;
  border-color: var(--ink) !important;
  background-color: var(--surface-raised) !important;
}
input:focus-visible, textarea:focus-visible, button:focus-visible,
[role="combobox"]:focus-visible {
  outline: 2px solid var(--focus) !important;
  outline-offset: 2px !important;
  box-shadow: none !important;
}
.stButton button, .stDownloadButton button {
  min-height: 2.75rem;
  border: 1px solid var(--ink) !important;
  border-radius: 0 !important;
  font-weight: 600;
  transition: transform 150ms ease, box-shadow 150ms ease, background-color 150ms ease;
}
.stButton button[kind="secondary"], .stDownloadButton button {
  background: var(--surface) !important;
  color: var(--ink) !important;
}
.stButton button[kind="primary"] {
  background: var(--ink) !important;
  color: var(--surface-raised) !important;
  box-shadow: 4px 4px 0 var(--accent) !important;
}
.stButton button[kind="primary"]:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 var(--accent) !important;
}
[data-testid="stAlert"] {
  border: 1px solid var(--line-strong) !important;
  border-left: 4px solid var(--accent) !important;
  border-radius: 0 !important;
  background: var(--accent-wash) !important;
}
[data-testid="stDataEditor"], [data-testid="stDataFrame"] { border: 1px solid var(--ink); }
[data-testid="stMetric"] {
  padding: 0.8rem 0;
  border-top: 2px solid var(--ink);
  border-bottom: 1px solid var(--line-strong);
}
[data-testid="stMetricLabel"] p {
  color: var(--ink-soft);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
[data-testid="stMetricValue"] { color: var(--accent); }
.stCaption, [data-testid="stCaptionContainer"] { color: var(--ink-soft); }

@media (max-width: 820px) {
  main .block-container { padding-top: 1.5rem; }
  .studio-hero { grid-template-columns: 1fr; gap: 1.5rem; }
  .studio-index { max-width: 420px; }
}
@media (max-width: 560px) {
  .studio-hero h1 { font-size: clamp(2.7rem, 14vw, 4rem) !important; }
  .studio-index { max-width: none; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: 0.01ms !important; }
}
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

st.markdown('''<header class="studio-hero">
  <div class="studio-hero__copy">
    <div class="eyebrow">Local document studio / Photography</div>
    <h1>Bookings <span>&amp;</span> invoices</h1>
    <p>Draft once. Generate a linked booking confirmation, invoice, and master agreement with Playwright. No cloud database or account required.</p>
  </div>
  <aside class="studio-index" aria-label="Generated document set">
    <div class="studio-index__label">Document set / 03</div>
    <ol>
      <li><span>01</span><strong>Master agreement</strong></li>
      <li><span>02</span><strong>Booking confirmation</strong></li>
      <li><span>03</span><strong>Invoice</strong></li>
    </ol>
  </aside>
</header>''', unsafe_allow_html=True)

with st.sidebar:
    st.subheader('Records')
    if st.button('＋ New booking', width='stretch'):
        fresh(); st.rerun()
    choices = list_records()
    picked = st.selectbox('Open saved booking', ['Select saved record'] + [p.stem for p in choices])
    if st.button('Load selected', disabled=picked == 'Select saved record', width='stretch'):
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
    df=st.data_editor(df, num_rows='dynamic', hide_index=True, width='stretch',
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
    extras=st.data_editor(extras, num_rows='dynamic', hide_index=True, width='stretch',
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
    if st.button('Save record',disabled=bool(error),width='stretch'):
        save_record(r);st.success('Saved locally.')
with right:
    if st.button('Generate 3 PDFs with Playwright',type='primary',disabled=bool(error),width='stretch'):
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
