"""Annotations must survive whatever the storage backend gives back.

Google Sheets returns everything as text, so a saved ``watchlist=True`` comes back
as the string ``"True"``. Anything that reaches ``merge_annotations`` — strings,
blanks, duplicates, junk ids — must never crash the dashboard.
"""

import pandas as pd
import pytest

from yc_scouter import user_data


def _companies():
    return pd.DataFrame([{"id": 101, "name": "A"}, {"id": 102, "name": "B"}])


def test_string_booleans_from_sheets_do_not_crash():
    sheet_like = pd.DataFrame(
        [
            {"id": "101", "watchlist": "True", "my_tags": "fav", "my_stage": "Contacted"},
            {"id": "102", "watchlist": "False", "my_tags": "", "my_stage": ""},
        ]
    )
    out = user_data.merge_annotations(_companies(), sheet_like).set_index("id")
    assert bool(out.loc[101, "watchlist"]) is True
    assert bool(out.loc[102, "watchlist"]) is False
    assert out.loc[101, "my_stage"] == "Contacted"
    assert out.loc[102, "my_stage"] == user_data.DEFAULT_STAGE


@pytest.mark.parametrize(
    "raw, expected",
    [
        (True, True),
        (False, False),
        ("True", True),
        ("true", True),
        ("TRUE", True),
        ("да", True),  # legacy spellings from the author's-language UI, still parsed
        ("yes", True),
        ("1", True),
        (1, True),
        ("ИСТИНА", True),  # ditto, uppercase
        ("False", False),
        ("false", False),
        ("FALSE", False),
        ("нет", False),  # the same word for "no" — must stay false
        ("0", False),
        (0, False),
        ("", False),
        (None, False),
        (float("nan"), False),
        ("что-то", False),  # arbitrary text is never true
    ],
)
def test_to_bool_accepts_every_backend_spelling(raw, expected):
    assert user_data.to_bool(raw) is expected


def test_duplicate_ids_do_not_multiply_rows():
    dupes = pd.DataFrame(
        [
            {"id": 101, "my_notes": "old"},
            {"id": 101, "my_notes": "new"},
        ]
    )
    out = user_data.merge_annotations(_companies(), dupes)
    assert len(out) == 2  # no row explosion
    assert out.set_index("id").loc[101, "my_notes"] == "new"  # last wins


def test_rows_with_unusable_ids_are_dropped():
    junk = pd.DataFrame(
        [
            {"id": None, "my_notes": "no id"},
            {"id": "abc", "my_notes": "garbage"},
            {"id": "101", "my_notes": "ok"},
        ]
    )
    out = user_data.merge_annotations(_companies(), junk).set_index("id")
    assert out.loc[101, "my_notes"] == "ok"
    assert out.loc[102, "my_notes"] == ""


def test_missing_columns_and_empty_store_are_fine():
    out = user_data.merge_annotations(_companies(), pd.DataFrame({"id": [101]}))
    assert len(out) == 2
    assert (out["my_notes"] == "").all()
    out2 = user_data.merge_annotations(_companies(), user_data.empty_user_frame())
    assert len(out2) == 2 and not out2["watchlist"].any()


def test_full_sheets_roundtrip_survives_stringification():
    """Simulate gsheets.save (everything -> str) then gsheets.load."""
    saved = user_data._ensure_columns(
        pd.DataFrame([{"id": 101, "watchlist": True, "my_notes": "a note", "my_stage": "Passed"}])
    )
    as_text = saved.fillna("").astype(str)  # what lands in the spreadsheet cells
    out = user_data.merge_annotations(_companies(), as_text).set_index("id")
    assert bool(out.loc[101, "watchlist"]) is True
    assert out.loc[101, "my_notes"] == "a note"
    assert out.loc[101, "my_stage"] == "Passed"


def test_nan_text_from_sheets_does_not_leak_into_notes():
    store = pd.DataFrame([{"id": 101, "my_notes": "nan", "my_tags": "None", "watchlist": ""}])
    out = user_data.merge_annotations(_companies(), store).set_index("id")
    assert out.loc[101, "my_notes"] == ""  # literal "nan" cleaned
    assert out.loc[101, "my_tags"] == ""
