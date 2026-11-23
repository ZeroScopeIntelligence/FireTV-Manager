from __future__ import annotations

import sys
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QPlainTextEdit,
    QTabWidget, QVBoxLayout, QWidget, QGroupBox, QListWidget
)

from app.config import load_settings, save_settings
from app.services.adb import ADBService, ADBError
from app.workers import Worker

STYLE = """
QMainWindow,QWidget{background:#101722;color:#e8eef7;font-size:10pt}
QTabWidget::pane{border:1px solid #2c3b50;border-radius:8px}
QTabBar::tab{background:#1a2635;padding:10px 16px;margin-right:3px}
QTabBar::tab:selected{background:#1769aa}
QLineEdit,QComboBox,QPlainTextEdit,QListWidget{background:#0b111a;border:1px solid #34465d;border-radius:6px;padding:8px;color:#edf4ff}
QPushButton{background:#1769aa;border:0;border-radius:6px;padding:9px 14px;color:white;font-weight:600}
QPushButton:hover{background:#2184d1}
QPushButton:disabled{background:#3b4654;color:#9ba7b5}
QGroupBox{border:1px solid #34465d;border-radius:8px;margin-top:12px;padding:12px;font-weight:600}
QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 5px}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.worker = None
        self.setWindowTitle("ZeroScope Fire TV Manager")
        self.resize(980, 680)
        self.setMinimumSize(800, 560)
        self.setStyleSheet(STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("ZEROSCOPE FIRE TV MANAGER")
        title.setStyleSheet("font-size:19pt;font-weight:800;color:#58b7ff")
        subtitle = QLabel("Fire OS device manager  •  Local network ADB")
        subtitle.setStyleSheet("color:#9aacc2")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch()
        self.status = QLabel("● Ready")
        self.status.setStyleSheet("color:#67d391;font-weight:700")
        header.addWidget(self.status)
        root.addLayout(header)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.device_tab = QWidget()
        self.install_tab = QWidget()
        self.apps_tab = QWidget()
        self.logs_tab = QWidget()
        self.settings_tab = QWidget()
        for widget, name in [
            (self.device_tab, "Devices"), (self.install_tab, "Install APK"),
            (self.apps_tab, "Installed Apps"), (self.logs_tab, "Logs"),
            (self.settings_tab, "Settings")
        ]:
            self.tabs.addTab(widget, name)

        self.build_devices()
        self.build_install()
        self.build_apps()
        self.build_logs()
        self.build_settings()
        self.refresh_devices()

    def service(self):
        return ADBService(self.settings.get("adb_path", ""))

    def log(self, message):
        self.log_view.appendPlainText(f"[{datetime.now():%H:%M:%S}] {message}")

    def set_busy(self, busy):
        for button in (
            self.discover_btn, self.connect_btn, self.refresh_btn,
            self.install_btn, self.load_apps_btn, self.uninstall_btn
        ):
            button.setEnabled(not busy)

    def work(self, fn, *args, label="Working", callback=None):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Please wait", "Another operation is running.")
            return
        self.log(label + "...")
        self.status.setText("● Working")
        self.set_busy(True)
        self.worker = Worker(fn, *args)
        self.worker.succeeded.connect(
            lambda result: self.work_done(result, label, callback)
        )
        self.worker.failed.connect(lambda error: self.work_failed(error, label))
        self.worker.finished.connect(lambda: self.set_busy(False))
        self.worker.start()

    def work_done(self, result, label, callback):
        self.status.setText("● Ready")
        self.status.setStyleSheet("color:#67d391;font-weight:700")
        self.log(label + ": completed")
        if callback:
            callback(result)

    def work_failed(self, error, label):
        self.status.setText("● Attention required")
        self.status.setStyleSheet("color:#ffbd69;font-weight:700")
        self.log(f"{label} failed: {error}")
        QMessageBox.warning(self, label, error)

    def port(self):
        try:
            value = int(self.port_input.text())
            if not 1 <= value <= 65535:
                raise ValueError
            return value
        except ValueError as exc:
            raise ADBError("Enter a valid TCP port.") from exc

    def build_devices(self):
        layout = QVBoxLayout(self.device_tab)
        group = QGroupBox("Discover Fire TV devices on your local network")
        form = QFormLayout(group)
        self.subnet_input = QLineEdit("192.168.1.0/24")
        self.port_input = QLineEdit(str(self.settings.get("default_port", 5555)))
        form.addRow("IPv4 subnet (CIDR)", self.subnet_input)
        form.addRow("ADB port", self.port_input)
        buttons = QHBoxLayout()
        self.discover_btn = QPushButton("Discover devices")
        self.discover_btn.clicked.connect(self.discover)
        self.connect_btn = QPushButton("Connect selected IP")
        self.connect_btn.clicked.connect(self.connect_ip)
        self.refresh_btn = QPushButton("Refresh ADB devices")
        self.refresh_btn.clicked.connect(self.refresh_devices)
        buttons.addWidget(self.discover_btn)
        buttons.addWidget(self.connect_btn)
        buttons.addWidget(self.refresh_btn)
        form.addRow(buttons)
        layout.addWidget(group)

        group2 = QGroupBox("Detected / connected devices")
        inner = QVBoxLayout(group2)
        self.device_combo = QComboBox()
        inner.addWidget(self.device_combo)
        self.device_output = QPlainTextEdit()
        self.device_output.setReadOnly(True)
        self.device_output.setPlaceholderText("ADB device output appears here.")
        inner.addWidget(self.device_output)
        layout.addWidget(group2)

    def build_install(self):
        layout = QVBoxLayout(self.install_tab)
        group = QGroupBox("Install an APK on your Fire TV")
        form = QFormLayout(group)
        self.apk_input = QLineEdit()
        self.apk_input.setPlaceholderText("Choose an APK file")
        browse = QPushButton("Browse...")
        browse.clicked.connect(self.browse_apk)
        row = QHBoxLayout()
        row.addWidget(self.apk_input)
        row.addWidget(browse)
        form.addRow("APK file", row)
        self.install_device = QComboBox()
        form.addRow("Target device", self.install_device)
        self.reinstall_check = QCheckBox(
            "Reinstall/update if the app is already installed"
        )
        self.reinstall_check.setChecked(True)
        form.addRow(self.reinstall_check)
        self.install_btn = QPushButton("Install APK")
        self.install_btn.clicked.connect(self.install_apk)
        form.addRow(self.install_btn)
        layout.addWidget(group)
        note = QLabel(
            "Install only APKs you trust. Fire TV may reject apps incompatible "
            "with its CPU architecture, Android version, or hardware."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#9aacc2")
        layout.addWidget(note)
        layout.addStretch()

    def build_apps(self):
        layout = QVBoxLayout(self.apps_tab)
        group = QGroupBox("Third-party installed packages")
        inner = QVBoxLayout(group)
        self.apps_device = QComboBox()
        inner.addWidget(self.apps_device)
        self.load_apps_btn = QPushButton("Load installed apps")
        self.load_apps_btn.clicked.connect(self.load_apps)
        inner.addWidget(self.load_apps_btn)
        self.package_list = QListWidget()
        inner.addWidget(self.package_list)
        self.uninstall_btn = QPushButton("Uninstall selected app")
        self.uninstall_btn.clicked.connect(self.uninstall_selected)
        inner.addWidget(self.uninstall_btn)
        layout.addWidget(group)

    def build_logs(self):
        layout = QVBoxLayout(self.logs_tab)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)
        clear = QPushButton("Clear logs")
        clear.clicked.connect(self.log_view.clear)
        layout.addWidget(clear)

    def build_settings(self):
        layout = QVBoxLayout(self.settings_tab)
        group = QGroupBox("Android Debug Bridge")
        form = QFormLayout(group)
        self.adb_input = QLineEdit(self.settings.get("adb_path", ""))
        self.adb_input.setPlaceholderText("/usr/bin/adb (usually auto-detected)")
        form.addRow("ADB executable path", self.adb_input)
        save = QPushButton("Save settings")
        save.clicked.connect(self.save_settings_ui)
        test = QPushButton("Test ADB")
        test.clicked.connect(
            lambda: self.work(
                self.service().version, label="ADB version check",
                callback=lambda output: QMessageBox.information(
                    self, "ADB available", output
                )
            )
        )
        buttons = QHBoxLayout()
        buttons.addWidget(save)
        buttons.addWidget(test)
        form.addRow(buttons)
        layout.addWidget(group)
        layout.addStretch()

    def discover(self):
        try:
            port = self.port()
        except ADBError as exc:
            QMessageBox.warning(self, "Port", str(exc))
            return
        self.work(
            self.service().discover, self.subnet_input.text().strip(), port,
            label="Network discovery", callback=self.discovery_done
        )

    def discovery_done(self, ips):
        if not ips:
            QMessageBox.information(
                self, "Discovery",
                "No endpoint responded on that port. Check ADB Debugging, IP, "
                "subnet and port."
            )
            return
        for address in ips:
            if self.device_combo.findText(address) < 0:
                self.device_combo.addItem(address)
        self.device_output.setPlainText(
            "Reachable ADB endpoints:\n" + "\n".join(ips)
        )
        self.log("Found endpoint(s): " + ", ".join(ips))

    def connect_ip(self):
        address = self.device_combo.currentText().strip()
        if not address:
            QMessageBox.information(
                self, "Select device", "Discover a Fire TV or select its IP first."
            )
            return
        try:
            port = self.port()
        except ADBError as exc:
            QMessageBox.warning(self, "Port", str(exc))
            return
        self.work(
            self.service().connect, address, port,
            label=f"Connecting to {address}", callback=self.after_connect
        )

    def after_connect(self, result):
        self.log(str(result))
        # The connect worker is still completing as this callback runs.
        # Query ADB synchronously here instead of starting a competing worker.
        try:
            self.devices_done(self.service().devices())
        except ADBError as exc:
            self.log(f"Could not refresh devices: {exc}")

    def refresh_devices(self):
        self.work(
            self.service().devices, label="Refreshing ADB devices",
            callback=self.devices_done
        )

    def devices_done(self, output):
        self.device_output.setPlainText(output)
        serials = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device" and parts[0] != "List":
                serials.append(parts[0])
        for combo in (self.install_device, self.apps_device):
            current = combo.currentText()
            combo.clear()
            combo.addItems(serials)
            if current and combo.findText(current) >= 0:
                combo.setCurrentText(current)
        self.log(f"{len(serials)} authorized device(s) available.")

    def browse_apk(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select APK", "", "Android package (*.apk)"
        )
        if path:
            self.apk_input.setText(path)

    def install_apk(self):
        serial = self.install_device.currentText()
        apk_path = self.apk_input.text().strip()
        if not apk_path:
            QMessageBox.information(self, "APK required", "Choose an APK file first.")
            return
        self.work(
            self.service().install_apk, serial, apk_path,
            self.reinstall_check.isChecked(), label="Installing APK",
            callback=self.show_result
        )

    def load_apps(self):
        self.work(
            self.service().packages, self.apps_device.currentText(),
            label="Loading installed apps", callback=self.packages_done
        )

    def packages_done(self, output):
        self.package_list.clear()
        for line in output.splitlines():
            package = line.strip()
            if package.startswith("package:"):
                self.package_list.addItem(package.removeprefix("package:"))
        self.log(f"Loaded {self.package_list.count()} third-party package(s).")

    def uninstall_selected(self):
        item = self.package_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select app", "Select an app package first.")
            return
        package = item.text()
        answer = QMessageBox.question(
            self, "Confirm uninstall", f"Uninstall {package} from this Fire TV?"
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.work(
            self.service().uninstall, self.apps_device.currentText(), package,
            label=f"Uninstalling {package}", callback=self.show_result
        )

    def show_result(self, output):
        self.log(str(output))
        QMessageBox.information(self, "ADB result", str(output))

    def save_settings_ui(self):
        self.settings["adb_path"] = self.adb_input.text().strip()
        try:
            self.settings["default_port"] = self.port()
        except ADBError:
            pass
        save_settings(self.settings)
        self.log("Settings saved.")
        QMessageBox.information(self, "Settings", "Settings saved.")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
