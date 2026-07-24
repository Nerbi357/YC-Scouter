"""Tests for personal annotations (keyed by immutable id) across refreshes."""

import pandas as pd

from yc_scouter import normalize, user_data


def test_merge_without_file_adds_empty_columns(tmp_path, sample_records):
    df = normalize.normalize(sample_records)
    out = user_data.merge_user_data(df, path=tmp_path / "user_data.csv")
    for col in ("my_rating", "watchlist", "my_tags", "my_stage", "my_notes"):
        assert col in out.columns
    assert (out["watchlist"] == False).all()  # noqa: E712
    assert (out["my_notes"] == "").all()
    assert (out["my_stage"] == user_data.DEFAULT_STAGE).all()


def test_save_and_merge_roundtrip_by_id(tmp_path, sample_records):
    path = tmp_path / "user_data.csv"
    user_data.save_user_data(
        [{"id": 101, "my_rating": 5, "watchlist": True, "my_notes": "hot lead"}],
        path=path,
    )
    df = normalize.normalize(sample_records)
    out = user_data.merge_user_data(df, path=path).set_index("id")
    assert out.loc[101, "my_rating"] == 5
    assert bool(out.loc[101, "watchlist"]) is True
    assert out.loc[101, "my_notes"] == "hot lead"


def test_refresh_preserves_annotations(tmp_path, sample_records):
    path = tmp_path / "user_data.csv"
    user_data.save_user_data(
        [{"id": 103, "my_rating": 4, "watchlist": True, "my_notes": "watch"}], path=path
    )
    for _ in range(2):  # simulate two independent refreshes
        df = normalize.normalize(sample_records)
        out = user_data.merge_user_data(df, path=path).set_index("id")
        assert out.loc[103, "my_rating"] == 4


def test_merge_is_idempotent(tmp_path, sample_records):
    path = tmp_path / "user_data.csv"
    user_data.save_user_data(
        [{"id": 101, "my_rating": 5, "watchlist": True, "my_notes": "hot"}], path=path
    )
    df = normalize.normalize(sample_records)
    once = user_data.merge_user_data(df, path=path)
    twice = user_data.merge_user_data(once, path=path)
    for col in ("my_rating", "watchlist", "my_notes"):
        assert col in twice.columns
        assert f"{col}_x" not in twice.columns and f"{col}_y" not in twice.columns
    assert twice.set_index("id").loc[101, "my_notes"] == "hot"


def test_stage_defaults_and_tags_roundtrip(tmp_path, sample_records):
    path = tmp_path / "user_data.csv"
    user_data.save_user_data(
        [{"id": 101, "my_stage": "Contacted", "my_tags": "favorite, ai"}], path=path
    )
    df = normalize.normalize(sample_records)
    out = user_data.merge_user_data(df, path=path).set_index("id")
    assert out.loc[101, "my_stage"] == "Contacted"
    assert out.loc[101, "my_tags"] == "favorite, ai"
    others = out.drop(index=101)
    assert (others["my_stage"] == user_data.DEFAULT_STAGE).all()


def test_load_missing_returns_empty_schema(tmp_path):
    ud = user_data.load_user_data(tmp_path / "nope.csv")
    assert list(ud.columns) == list(user_data.USER_COLUMNS)
    assert user_data.USER_COLUMNS[0] == "id"
    assert len(ud) == 0
    assert isinstance(ud, pd.DataFrame)


def test_migrate_slug_to_id(tmp_path, sample_records):
    df = normalize.normalize(sample_records)  # has both id and slug
    old = tmp_path / "user_data_old.csv"
    pd.DataFrame(
        [
            {
                "slug": "acme-ai",
                "my_rating": 5,
                "watchlist": True,
                "my_notes": "hot",
                "my_tags": "fav",
                "my_stage": "Contacted",
            },
            {"slug": "does-not-exist", "my_rating": 1, "my_notes": "orphan"},
        ]
    ).to_csv(old, index=False)

    out = tmp_path / "user_data.csv"
    migrated = user_data.migrate_slug_to_id(old, df, out_path=out, backup=False)

    assert list(migrated.columns) == list(user_data.USER_COLUMNS)
    m = migrated.set_index("id")
    assert 101 in m.index and m.loc[101, "my_notes"] == "hot"  # acme-ai -> id 101
    assert len(migrated) == 1  # unmapped slug dropped
    # written to disk and reloadable by id
    reloaded = user_data.load_user_data(out).set_index("id")
    assert reloaded.loc[101, "my_tags"] == "fav"
