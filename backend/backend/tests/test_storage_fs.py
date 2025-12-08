from pathlib import Path

from app.artifacts_storage.fs import FSStorage


def test_fs_storage_put_exists_and_url(tmp_path: Path):
    store = FSStorage(root=tmp_path)

    # prepare source file
    src = tmp_path / "src.mp4"
    src.write_bytes(b"MP4")

    key = "job123/final.mp4"
    store.put_file(key, str(src))

    assert store.exists(key) is True
    url = store.get_url(key)
    assert url == "/artifacts/job123/final.mp4"
