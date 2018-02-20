import django
django.setup()
from datetime import date, timedelta
from nba_stats.utils import *


def setup_func():
    pass


def teardown_func():
    pass

# For now I'm just going to write tests for green light scenarios


def test_convert_height_to_inches():
    assert convert_height_to_int("6-7") == 79


def test_convert_datetime_string_to_date_instance():
    datestr = "2017-01-30T00:00:00"
    date_obj = date(2017, 1, 30)
    assert convert_datetime_string_to_date_instance(datestr) == date_obj


def test_make_season_int():
    easy = make_season_int("2016-17")
    hard = make_season_int("1999-00")
    assert easy == 2016
    assert hard == 1999


def test_make_season_str():
    easy = make_season_str(2016)
    medium = make_season_str(1999)
    hard = make_season_str(2005)
    assert easy == "2016-17"
    assert medium == "1999-00"
    assert hard == "2005-06"


def test_intify_arena_capacity():
    arena_cap = "19,361"
    assert intify_arena_capacity(arena_cap) == 19361


def test_dictify():
    headers = ["foo", "bar"]
    rows = [[1, 2], [3, 4]]
    rset = {'headers': headers, 'rowSet': rows}
    result = dictify(rset)
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], dict)
    assert result[1]['bar'] == 4


def test_convert_colon_tstamp_to_duration():
    dur = timedelta(hours=2, minutes=30)
    assert convert_colon_tstamp_to_duration("2:30") == dur


def test_convert_min_sec_to_float():
    assert convert_min_sec_to_float("24:36") == 24.6
