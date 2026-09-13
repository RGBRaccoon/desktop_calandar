from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QImageReader


def read_background(path: Path) -> QImage:
    if not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("32MB 이하의 JPG 또는 PNG 파일을 선택하세요.")
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    size = reader.size()
    if (
        bytes(reader.format().data()).lower() not in (b"png", b"jpeg", b"jpg")
        or size.width() * size.height() > 32_000_000
    ):
        raise ValueError("지원하지 않는 이미지입니다. 3,200만 화소 이하 JPG/PNG를 선택하세요.")
    image = reader.read()
    if image.isNull():
        raise ValueError("이미지를 읽을 수 없습니다. 다른 JPG/PNG를 선택하세요.")
    if max(image.width(), image.height()) > 4096:
        image = image.scaled(
            4096,
            4096,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return image


def import_background(source: Path, directory: Path) -> Path:
    image = read_background(source)
    destination = directory / "backgrounds"
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{uuid4().hex}.png"
    if not image.save(str(target)):
        target.unlink(missing_ok=True)
        raise OSError("배경 이미지를 저장하지 못했습니다.")
    return target


def remove_managed_background(path: Path, directory: Path) -> None:
    """Remove only a background file previously copied into this app data directory."""
    managed_directory = (directory / "backgrounds").resolve()
    try:
        target = path.resolve()
    except OSError:
        return
    if target.parent == managed_directory and target.suffix.lower() == ".png":
        target.unlink(missing_ok=True)
