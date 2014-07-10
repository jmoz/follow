from nose.tools import *
from dateutil import parser

from model import Twitter, is_older_than_days


def test_date_comparison():
    # test date comparison
    date_to_compare = parser.parse(u'Thu Nov 23 11:09:20 +0000 2013').replace(tzinfo=None)
    date_22 = u'Thu Nov 22 11:09:20 +0000 2013'
    date_20 = u'Thu Nov 20 11:09:20 +0000 2013'

    assert_false(is_older_than_days(date_22, 2, date_to_compare))
    assert_true(is_older_than_days(date_20, 2, date_to_compare))
