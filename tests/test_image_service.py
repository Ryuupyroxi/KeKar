from pathlib import Path

from PIL import Image

from src.services import image_service


def _make_image(path: Path, size=(4000, 3000)) -> None:
    Image.new("RGB", size, (120, 80, 40)).save(path, "JPEG")


def test_import_resizes_and_saves(tmp_path, monkeypatch):
    monkeypatch.setattr(image_service, "photos_dir", lambda: tmp_path / "photos")
    src = tmp_path / "big.jpg"
    _make_image(src)
    out = image_service.import_photos(7, [src])
    assert len(out) == 1
    with Image.open(out[0]) as im:
        assert max(im.size) <= image_service.MAX_DIMENSION
    assert out[0].parent.name == "7"


def test_property_photos_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(image_service, "photos_dir", lambda: tmp_path / "photos")
    src = tmp_path / "a.jpg"
    _make_image(src, (800, 600))
    image_service.import_photos(3, [src])
    assert len(image_service.property_photos(3)) == 1
    image_service.delete_property_photos(3)
    assert image_service.property_photos(3) == []


def test_thumbnail_is_small(tmp_path, monkeypatch):
    monkeypatch.setattr(image_service, "photos_dir", lambda: tmp_path / "photos")
    src = tmp_path / "t.jpg"
    _make_image(src, (1200, 900))
    thumb = image_service.thumbnail(src, size=200)
    with Image.open(thumb) as im:
        assert max(im.size) <= 200
