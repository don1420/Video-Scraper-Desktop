import sys

from PySide6.QtCore import QThread, Qt, QUrl, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ffmpeg import build_ffmpeg_command, download_videos
from scraper import process_video_details


class ScrapeWorker(QThread):
    progress = Signal(float)
    completed = Signal(list)
    failed = Signal(str)

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url

    def run(self) -> None:
        try:
            results = process_video_details(
                self.url,
                progress_callback=self.progress.emit,
            )
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.completed.emit(results)


class DownloadWorker(QThread):
    progress = Signal(object, str)
    completed = Signal(list)
    failed = Signal(str)

    def __init__(
        self,
        video_sources: list[str],
        output_directory: str,
        start_index: int = 1,
        output_indices: list[int] | None = None,
    ) -> None:
        super().__init__()
        self.video_sources = video_sources
        self.output_directory = output_directory
        self.start_index = start_index
        self.output_indices = output_indices

    def run(self) -> None:
        try:
            files = download_videos(
                self.video_sources,
                self.output_directory,
                progress_callback=self.progress.emit,
                start_index=self.start_index,
                output_indices=self.output_indices,
            )
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.completed.emit(files)


class VideoScraperWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.worker: QThread | None = None
        self.video_sources: list[str] = []
        self.video_checkboxes: list[QCheckBox] = []
        self.setWindowTitle("Video Scraper")
        self.setMinimumSize(820, 680)
        self.resize(1040, 780)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("Video Scraper")
        title.setObjectName("title")
        subtitle = QLabel(
            "Extract playlist videos, download them, or generate FFmpeg commands."
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
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.hide()

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status")
        self.status_label.hide()

        self.select_all_checkbox = QCheckBox("Select all videos")
        self.select_all_checkbox.setEnabled(False)
        self.select_all_checkbox.stateChanged.connect(self.toggle_all_videos)

        self.selection_count_label = QLabel("No videos loaded")
        self.selection_count_label.setObjectName("status")

        self.video_list = QWidget()
        self.video_list_layout = QVBoxLayout(self.video_list)
        self.video_list_layout.setContentsMargins(8, 8, 8, 8)
        self.video_list_layout.setSpacing(4)
        self.video_list_layout.addStretch(1)

        video_scroll_area = QScrollArea()
        video_scroll_area.setWidgetResizable(True)
        video_scroll_area.setWidget(self.video_list)
        video_scroll_area.setObjectName("videoList")
        video_tab = QWidget()
        video_tab_layout = QVBoxLayout(video_tab)
        video_tab_layout.addWidget(self.select_all_checkbox)
        video_tab_layout.addWidget(self.selection_count_label)
        video_tab_layout.addWidget(video_scroll_area, 1)

        self.results = QPlainTextEdit()
        self.results.setReadOnly(True)
        self.results.setPlaceholderText(
            "Your FFmpeg commands will appear here after scraping."
        )
        self.results.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.tabs = QTabWidget()
        self.tabs.addTab(video_tab, "Videos")
        self.tabs.addTab(self.results, "FFmpeg commands")

        self.copy_button = QPushButton("Copy commands")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_commands)

        self.save_button = QPushButton("Save to file")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_commands)

        self.download_button = QPushButton("Download videos")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.start_download)

        self.source_download_button = QPushButton("Download selected videos")
        self.source_download_button.setEnabled(False)
        self.source_download_button.clicked.connect(self.start_selected_download)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear)

        actions = QHBoxLayout()
        actions.addWidget(self.source_download_button)
        actions.addWidget(self.download_button)
        actions.addStretch(1)
        actions.addWidget(self.copy_button)
        actions.addWidget(self.save_button)
        actions.addWidget(self.clear_button)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addLayout(input_row)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.tabs, 1)
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
            QScrollArea#videoList {
                background: white;
                border: 1px solid #d5dbea;
                border-radius: 8px;
            }
            QTabWidget::pane {
                background: white;
                border: 1px solid #d5dbea;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #e9edf5;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                color: #315efb;
                font-weight: 600;
            }
            QCheckBox {
                spacing: 8px;
                padding: 7px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
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
            self.progress_bar.hide()
            self.status_label.setText("Enter a valid HTTP or HTTPS playlist URL.")
            self.status_label.show()
            return

        self.progress_bar.show()
        self.status_label.show()
        self.results.clear()
        self.video_sources.clear()
        self.clear_video_list()
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.select_all_checkbox.setEnabled(False)
        self.selection_count_label.setText("Loading videos…")
        self.source_download_button.setEnabled(False)
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

    def show_results(
        self,
        video_details: list[tuple[str, str | None]],
    ) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        if not video_details:
            self.select_all_checkbox.setEnabled(False)
            self.selection_count_label.setText("No videos loaded")
            self.status_label.setText(
                "Scraping finished, but no video sources were found."
            )
            return

        video_sources = [video_src for video_src, _ in video_details]
        self.video_sources = video_sources
        self.clear_video_list()
        for index, (_, title) in enumerate(video_details, start=1):
            label = f"{title} - {index}" if title else f"Video {index}"
            checkbox = QCheckBox(label)
            checkbox.setToolTip(video_sources[index - 1])
            checkbox.stateChanged.connect(self.update_selection_state)
            self.video_checkboxes.append(checkbox)
            self.video_list_layout.insertWidget(
                self.video_list_layout.count() - 1,
                checkbox,
            )
        self.select_all_checkbox.setEnabled(bool(video_sources))
        self.update_selection_state()
        commands = [
            build_ffmpeg_command(video_url, index)
            for index, video_url in enumerate(video_sources, start=1)
        ]
        self.results.setPlainText("\n".join(commands))
        self.copy_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.download_button.setEnabled(True)
        self.status_label.setText(f"Done — generated {len(commands)} command(s).")

    def show_error(self, message: str) -> None:
        self.progress_bar.hide()
        self.status_label.show()
        self.status_label.setText(f"Operation failed: {message}")

    def scraping_finished(self) -> None:
        self.start_button.setEnabled(True)
        self.worker = None

    def start_download(self) -> None:
        if not self.video_sources:
            return

        self._start_download(
            self.video_sources,
            list(range(1, len(self.video_sources) + 1)),
        )

    def start_selected_download(self) -> None:
        selected_indices = [
            index
            for index, checkbox in enumerate(self.video_checkboxes)
            if checkbox.isChecked()
        ]
        if not selected_indices:
            return

        self._start_download(
            [self.video_sources[index] for index in selected_indices],
            [index + 1 for index in selected_indices],
        )

    def _start_download(
        self,
        video_sources: list[str],
        output_indices: list[int],
    ) -> None:
        output_directory = QFileDialog.getExistingDirectory(
            self,
            "Choose download folder",
        )
        if not output_directory:
            return

        self.start_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.select_all_checkbox.setEnabled(False)
        for checkbox in self.video_checkboxes:
            checkbox.setEnabled(False)
        self.source_download_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label.setText("Preparing downloads…")

        self.worker = DownloadWorker(
            video_sources,
            output_directory,
            output_indices=output_indices,
        )
        self.worker.progress.connect(self.download_progress)
        self.worker.completed.connect(self.download_completed)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.download_finished)
        self.worker.start()

    def download_progress(self, progress: float | None, message: str) -> None:
        if progress is None:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(round(progress * 100))
        self.status_label.setText(message)

    def download_completed(self, files: list[str]) -> None:
        self.progress_bar.setValue(100)
        count = len(files)
        video_label = "video" if count == 1 else "videos"
        self.status_label.setText(f"Downloaded {count} {video_label}.")

    def download_finished(self) -> None:
        self.start_button.setEnabled(True)
        self.download_button.setEnabled(bool(self.video_sources))
        self.select_all_checkbox.setEnabled(bool(self.video_sources))
        for checkbox in self.video_checkboxes:
            checkbox.setEnabled(True)
        self.update_selection_state()
        self.clear_button.setEnabled(True)
        self.worker = None

    def toggle_all_videos(self, state: int) -> None:
        if state == Qt.CheckState.PartiallyChecked.value:
            return

        checked = state == Qt.CheckState.Checked.value
        for checkbox in self.video_checkboxes:
            checkbox.setChecked(checked)
        self.update_selection_state()

    def update_selection_state(self, _state: int | None = None) -> None:
        selected_count = sum(
            checkbox.isChecked() for checkbox in self.video_checkboxes
        )
        total = len(self.video_checkboxes)
        if selected_count == total and total:
            check_state = Qt.CheckState.Checked
        elif selected_count:
            check_state = Qt.CheckState.PartiallyChecked
        else:
            check_state = Qt.CheckState.Unchecked

        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setCheckState(check_state)
        self.select_all_checkbox.blockSignals(False)
        self.selection_count_label.setText(
            f"{selected_count} of {total} selected"
            if total
            else "No videos loaded"
        )
        self.source_download_button.setEnabled(selected_count > 0)

    def clear_video_list(self) -> None:
        self.video_checkboxes.clear()
        while self.video_list_layout.count():
            item = self.video_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.video_list_layout.addStretch(1)
        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        self.select_all_checkbox.blockSignals(False)

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
        self.video_sources.clear()
        self.clear_video_list()
        self.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        self.select_all_checkbox.setEnabled(False)
        self.selection_count_label.setText("No videos loaded")
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
        self.progress_bar.hide()
        self.status_label.hide()
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.source_download_button.setEnabled(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(
                self,
                "Operation in progress",
                "Wait for the current operation to finish before closing.",
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
