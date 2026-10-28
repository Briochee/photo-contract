from decimal import Decimal
import pytest
from core import totals, money, due_date

def test_total_and_approved_additions():
    x=totals([{'description':'Photography','quantity':1,'rate':'800.00'}],
             [{'description':'Approved travel','quantity':'2','rate':'35.50','approved':True}], '12.34')
    assert x['booking_subtotal']==Decimal('800.00')
    assert x['extra_subtotal']==Decimal('71.00')
    assert x['grand_total']==Decimal('883.34')

def test_unapproved_addition_blocked():
    with pytest.raises(ValueError,match='written approval'):
        totals([], [{'description':'Rental','quantity':1,'rate':150,'approved':False}])

def test_no_negative_or_zero_qty():
    with pytest.raises(ValueError):
        totals([{'description':'Fee','quantity':0,'rate':20}], [])

def test_due_date():
    assert due_date('2026-10-28',15)=='2026-11-12'

def test_decimal_rounding():
    assert money('12.345')==Decimal('12.35')
