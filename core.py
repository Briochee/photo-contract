"""Pure pricing and reference logic. Never use floating point for money."""
from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import json
import re
import sqlite3

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)


def money(value):
    try:
        d = Decimal(str(value if value not in ('', None) else '0'))
        if not d.is_finite():
            raise ValueError('Amounts must be finite')
        return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f'Invalid monetary amount: {value!r}') from exc


def dollars(value):
    d = money(value)
    return f'${d:,.2f}' if d >= 0 else f'-${abs(d):,.2f}'


def normalize_lines(lines, *, require_approved=False):
    output = []
    for line in lines:
        label = str(line.get('description') or '').strip()
        if not label:
            continue
        qty = money(line.get('quantity', 1))
        rate = money(line.get('rate', 0))
        if qty <= 0 or rate < 0:
            raise ValueError('Line item quantities must be positive, and rates cannot be negative.')
        if require_approved and not line.get('approved', False):
            raise ValueError(f'Additional invoice charge "{label}" must have written approval confirmed.')
        output.append({'description': label, 'quantity': str(qty), 'rate': str(rate),
                       'amount': str(money(qty * rate)),
                       'approved': bool(line.get('approved', False))})
    return output


def totals(booking_lines, invoice_extras, tax_amount='0', *, check_approval=True):
    base = normalize_lines(booking_lines)
    extras = normalize_lines(invoice_extras, require_approved=check_approval)
    tax = money(tax_amount)
    if tax < 0:
        raise ValueError('Tax amount cannot be negative.')
    booking_total = sum((money(x['amount']) for x in base), Decimal('0'))
    additional_total = sum((money(x['amount']) for x in extras), Decimal('0'))
    return {'booking_lines': base, 'extra_lines': extras,
            'booking_subtotal': booking_total, 'extra_subtotal': additional_total,
            'subtotal': booking_total + additional_total, 'tax': tax,
            'grand_total': money(booking_total + additional_total + tax)}


def next_references(year=None):
    year = int(year or date.today().year)
    with sqlite3.connect(DATA / 'references.sqlite3', timeout=15) as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS sequences (year INTEGER PRIMARY KEY, seq INTEGER NOT NULL)')
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('INSERT INTO sequences (year, seq) VALUES (?, 0) ON CONFLICT(year) DO NOTHING', (year,))
        connection.execute('UPDATE sequences SET seq=seq+1 WHERE year=?', (year,))
        num = connection.execute('SELECT seq FROM sequences WHERE year=?', (year,)).fetchone()[0]
    return f'BK-{year}-{num:03d}', f'INV-{year}-{num:03d}'


def record_path(ref):
    if not re.fullmatch(r'BK-\d{4}-\d{3,}', str(ref)):
        raise ValueError('Invalid booking reference')
    return DATA / f'{ref}.json'


def save_record(record):
    path = record_path(record['booking_ref'])
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
    tmp.replace(path)
    return path


def list_records():
    return sorted(DATA.glob('BK-*.json'), reverse=True)


def due_date(invoice_date, net_days):
    return (date.fromisoformat(invoice_date) + timedelta(days=int(net_days))).isoformat()
