from unittest.mock import Mock, patch

import pytest
from PySide6.QtGui import QColor, QImage

from desktop_calendar.repositories.event_repository import EventRepository
from desktop_calendar.services.background_service import (
    import_background,
    read_background,
    remove_managed_background,
)
from desktop_calendar.services.settings_service import SettingsService
from desktop_calendar.ui.main_window import MainWindow
from desktop_calendar.ui.settings_dialog import SettingsDialog


def make_image(path):
    image = QImage(200, 100, QImage.Format.Format_RGB32)
    image.fill(QColor("#ff0000"))
    assert image.save(str(path))


def test_background_copy_survives_source_removal(tmp_path):
    source = tmp_path / "source.png"
    make_image(source)
    target = import_background(source, tmp_path / "app")
    source.unlink()
    assert target.parent == tmp_path / "app" / "backgrounds"
    assert not read_background(target).isNull()


def test_invalid_image_does_not_create_background(tmp_path):
    source = tmp_path / "bad.png"
    source.write_text("not an image")
    with pytest.raises(ValueError):
        import_background(source, tmp_path / "app")
    assert not (tmp_path / "app").exists()


def test_cleanup_only_removes_app_managed_background(tmp_path):
    source = tmp_path / "source.png"
    external = tmp_path / "external.png"
    make_image(source)
    make_image(external)
    target = import_background(source, tmp_path / "app")
    remove_managed_background(external, tmp_path / "app")
    remove_managed_background(target, tmp_path / "app")
    assert external.is_file()
    assert not target.exists()


def test_settings_cancel_keeps_original_background(app, tmp_path):
    source = tmp_path / "source.png"
    make_image(source)
    config = SettingsService(tmp_path / "config.json").load()
    dialog = SettingsDialog(config)
    with patch(
        "desktop_calendar.ui.settings_dialog.QFileDialog.getOpenFileName",
        return_value=(str(source), ""),
    ):
        dialog.choose_image()
    dialog.reject()
    assert config["background_image"] == ""
    assert not (tmp_path / "backgrounds").exists()


def test_background_render_and_restart(app, tmp_path):
    source = tmp_path / "source.png"
    make_image(source)
    settings = SettingsService(tmp_path / "app/config.json")
    config = settings.load()
    config.update(
        background_image=str(import_background(source, settings.path.parent)),
        image_opacity=1.0,
        image_brightness=1.0,
    )
    settings.save(config)
    source.unlink()
    window = MainWindow(settings, EventRepository(tmp_path / "cache.db"), Mock(), auto_sync=False)
    try:
        window.reveal()
        app.processEvents()
        color = window.grab().toImage().pixelColor(1, 1)
        assert color.red() > 240 and color.green() < 10
        window.config["image_brightness"] = 0.0
        window.apply_appearance()
        assert window.grab().toImage().pixelColor(1, 1).red() < 10
        window.config["image_opacity"] = 0.0
        window.apply_appearance()
        assert window.grab().toImage().pixelColor(1, 1) == window.background_color
        window.config["background_image"] = ""
        window.apply_appearance()
        assert window.background_image.isNull()
    finally:
        window.tray.hide()
        window.quitting = True
        window.close()


def test_invalid_numeric_settings_fall_back(tmp_path):
    settings = SettingsService(tmp_path / "config.json")
    settings.path.write_text('{"image_opacity": "bad", "image_brightness": 10}')
    config = settings.load()
    assert config["image_opacity"] == 0.8
    assert config["image_brightness"] == 1.0
