import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Desktop Calendar · 설정")
        self.resize(420, 600)
        self.config = copy.deepcopy(config)
        self.action = "save"
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.startup = QCheckBox("Windows 로그인 시 자동 실행")
        self.startup.setChecked(config["startup"])
        form.addRow(self.startup)
        self.weekday = QComboBox()
        self.weekday.addItems(["월요일", "일요일"])
        self.weekday.setCurrentIndex(0 if config["first_weekday"] == 0 else 1)
        form.addRow("시작 요일", self.weekday)
        self.sync = QSpinBox()
        self.sync.setRange(1, 60)
        self.sync.setSuffix(" 분")
        self.sync.setValue(config["sync_minutes"])
        form.addRow("동기화 주기", self.sync)
        self.theme = QComboBox()
        self.theme.addItems(["Dark", "Light"])
        self.theme.setCurrentIndex(0 if config["theme"] == "dark" else 1)
        form.addRow("테마", self.theme)
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.35, 1)
        self.opacity.setSingleStep(0.05)
        self.opacity.setValue(config["window"]["opacity"])
        form.addRow("창 투명도", self.opacity)
        color = QPushButton("배경색 선택")
        color.clicked.connect(self.choose_color)
        reset = QPushButton("기본 배경색")
        reset.clicked.connect(lambda: self.config.update(background=""))
        color_row = QHBoxLayout()
        color_row.addWidget(color)
        color_row.addWidget(reset)
        form.addRow("배경", color_row)
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 18)
        self.font_size.setValue(config["font_size"])
        form.addRow("글자 크기", self.font_size)
        self.limit = QSpinBox()
        self.limit.setRange(1, 5)
        self.limit.setValue(config["event_limit"])
        form.addRow("날짜별 일정 수", self.limit)
        layout.addLayout(form)
        layout.addWidget(QLabel("Google Calendar · 읽기 전용"))
        self.client_file = QLineEdit(config["client_file"])
        self.client_file.setPlaceholderText("Google Desktop OAuth 인증 JSON")
        layout.addWidget(self.client_file)
        browse = QPushButton("인증 JSON 선택…")
        browse.clicked.connect(self.browse)
        layout.addWidget(browse)
        self.calendars = QListWidget()
        selected = config["calendar_ids"]
        for calendar in config["calendars"]:
            item = QListWidgetItem(calendar.get("summary", calendar["id"]))
            item.setData(Qt.ItemDataRole.UserRole, calendar["id"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if selected is None or calendar["id"] in selected
                else Qt.CheckState.Unchecked
            )
            self.calendars.addItem(item)
        layout.addWidget(self.calendars)
        login = QPushButton("Google 연결 / 다시 로그인")
        login.clicked.connect(lambda: self.finish("login"))
        logout = QPushButton("로그아웃 · 이 PC의 일정 캐시 삭제")
        logout.clicked.connect(lambda: self.finish("logout"))
        layout.addWidget(login)
        layout.addWidget(logout)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(lambda: self.finish("save"))
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_color(self):
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self.config["background"] = color.name()

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Desktop OAuth 인증 JSON", "", "JSON (*.json)")
        if path:
            self.client_file.setText(path)

    def finish(self, action):
        self.action = action
        self.config.update(
            startup=self.startup.isChecked(),
            first_weekday=0 if self.weekday.currentIndex() == 0 else 6,
            sync_minutes=self.sync.value(),
            theme="dark" if self.theme.currentIndex() == 0 else "light",
            font_size=self.font_size.value(),
            event_limit=self.limit.value(),
            client_file=self.client_file.text().strip(),
        )
        self.config["window"]["opacity"] = self.opacity.value()
        if self.calendars.count():
            self.config["calendar_ids"] = [
                self.calendars.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.calendars.count())
                if self.calendars.item(i).checkState() == Qt.CheckState.Checked
            ]
        self.accept()
