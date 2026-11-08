import sys

from PySide6.QtCore import QThread, QUrl, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scraper import process_url


class ScrapeWorker(QThread):
    progress = Signal(float)
    completed = Signal(list)
    failed = Signal(str)

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url

    def run(self) -> None:
        try:
            results = process_url(self.url, progress_callback=self.progress.emit)
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.completed.emit(results)


class VideoScraperWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.worker: ScrapeWorker | None = None
        self.setWindowTitle("Video Scraper")
        self.setMinimumSize(720, 560)
        self.resize(900, 680)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("Video Scraper")
        title.setObjectName("title")
        subtitle = QLabel(
            "Extract video sources from a playlist and generate FFmpeg commands."
        )
        subtitle.setObjectName("subtitle")

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/playlist")
        self.url_input.setClearButtonEnabled(True)
        self.url_input.returnPressed.connect(self.start_scraping)

        self.start_button = QPushButton("Start scraping")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.start_scraping)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        input_row.addWidget(self.url_input, 1)
        input_row.addWidget(self.start_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status")

        results_label = QLabel("Generated commands")
        results_label.setObjectName("sectionTitle")
        self.results = QPlainTextEdit()
        self.results.setReadOnly(True)
        self.results.setPlaceholderText(
            "Your FFmpeg commands will appear here after scraping."
        )
        self.results.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.copy_button = QPushButton("Copy commands")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_commands)

        self.save_button = QPushButton("Save to file")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_commands)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear)

        actions = QHBoxLayout()
        actions.addWidget(self.copy_button)
        actions.addWidget(self.save_button)
        actions.addStretch(1)
        actions.addWidget(self.clear_button)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addLayout(input_row)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(results_label)
        layout.addWidget(self.results, 1)
        layout.addLayout(actions)
        self.setCentralWidget(root)
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #f5f7fb;
                color: #172033;
                font-family: "Segoe UI", "Noto Sans", sans-serif;
                font-size: 14px;
            }
            QLabel#title {
                font-size: 28px;
                font-weight: 700;
            }
            QLabel#subtitle, QLabel#status {
                color: #64708a;
            }
            QLabel#sectionTitle {
                font-size: 15px;
                font-weight: 600;
            }
            QLineEdit, QPlainTextEdit {
                background: white;
                border: 1px solid #d5dbea;
                border-radius: 8px;
                padding: 10px;
                selection-background-color: #315efb;
            }
            QLineEdit:focus, QPlainTextEdit:focus {
                border: 1px solid #315efb;
            }
            QPushButton {
                background: white;
                border: 1px solid #d5dbea;
                border-radius: 8px;
                padding: 9px 14px;
            }
            QPushButton:hover:enabled {
                background: #edf1fa;
            }
            QPushButton:disabled {
                color: #9aa3b5;
            }
            QPushButton#primaryButton {
                background: #315efb;
                border-color: #315efb;
                color: white;
                font-weight: 600;
                padding-left: 18px;
                padding-right: 18px;
            }
            QPushButton#primaryButton:hover:enabled {
                background: #244de0;
            }
            QProgressBar {
                background: #e5e9f2;
                border: 0;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: #315efb;
                border-radius: 4px;
            }
            """
        )

    def start_scraping(self) -> None:
        url = self.url_input.text().strip()
        parsed_url = QUrl(url)
        if (
            not parsed_url.isValid()
            or parsed_url.scheme().lower() not in ("http", "https")
            or not parsed_url.host()
        ):
            self.status_label.setText("Enter a valid HTTP or HTTPS playlist URL.")
            return

        self.results.clear()
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Loading playlist and processing videos…")

        self.worker = ScrapeWorker(url)
        self.worker.progress.connect(self.update_progress)
        self.worker.completed.connect(self.show_results)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.scraping_finished)
        self.worker.start()

    def update_progress(self, progress: float) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(round(progress * 100))
        self.status_label.setText(f"Processing videos… {round(progress * 100)}%")

    def show_results(self, commands: list[str]) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        if not commands:
            self.status_label.setText(
                "Scraping finished, but no video sources were found."
            )
            return

        self.results.setPlainText("\n".join(commands))
        self.copy_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.status_label.setText(f"Done — generated {len(commands)} command(s).")

    def show_error(self, message: str) -> None:
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Scraping failed: {message}")

    def scraping_finished(self) -> None:
        self.start_button.setEnabled(True)
        self.worker = None

    def copy_commands(self) -> None:
        commands = self.results.toPlainText()
        if commands:
            QApplication.clipboard().setText(commands)
            self.status_label.setText("Commands copied to clipboard.")

    def save_commands(self) -> None:
        commands = self.results.toPlainText()
        if not commands:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save FFmpeg commands",
            "ffmpeg_commands.txt",
            "Text files (*.txt);;All files (*)",
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8", newline="\n") as output_file:
                output_file.write(commands)
        except OSError as error:
            QMessageBox.critical(self, "Unable to save file", str(error))
            return
        self.status_label.setText(f"Commands saved to {path}")

    def clear(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.url_input.clear()
        self.results.clear()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(
                self,
                "Scraping in progress",
                "Wait for the current scraping operation to finish before closing.",
            )
            event.ignore()
            return
        event.accept()


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("Video Scraper")
    window = VideoScraperWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
