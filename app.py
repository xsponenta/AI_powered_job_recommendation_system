import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QProgressBar
)
from PySide6.QtCore import QThread, Signal
from core.job_recommender import recommend_jobs


class JobWorker(QThread):
    finished = Signal(object)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        result = recommend_jobs(self.query)
        self.finished.emit(result)


class ProfileTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.role = QLineEdit()
        self.skills = QTextEdit()
        self.summary = QTextEdit()

        layout.addWidget(QLabel("Target Role / Keywords"))
        layout.addWidget(self.role)

        layout.addWidget(QLabel("Skills (comma separated)"))
        layout.addWidget(self.skills)

        layout.addWidget(QLabel("Professional Summary"))
        layout.addWidget(self.summary)

        self.setLayout(layout)

    def build_query(self):
        return f"{self.role.text() if self.role.text() else ""} {self.skills.toPlainText()}"


class JobsTab(QWidget):
    def __init__(self, profile_tab: ProfileTab):
        super().__init__()
        self.profile_tab = profile_tab

        layout = QVBoxLayout()

        self.fetch_btn = QPushButton("Fetch & Rank Jobs")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Title", "Company", "Source", "Score", "URL"]
        )

        self.fetch_btn.clicked.connect(self.fetch_jobs)

        layout.addWidget(self.fetch_btn)
        layout.addWidget(self.progress)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def fetch_jobs(self):
        query = self.profile_tab.build_query()
        if not query.strip():
            return

        self.progress.show()
        self.worker = JobWorker(query)
        self.worker.finished.connect(self.display_jobs)
        self.worker.start()

    def display_jobs(self, df):
        self.progress.hide()
        self.table.setRowCount(len(df))

        for row, (_, job) in enumerate(df.iterrows()):
            self.table.setItem(row, 0, QTableWidgetItem(job["title"]))
            self.table.setItem(row, 1, QTableWidgetItem(job["company"]))
            self.table.setItem(row, 2, QTableWidgetItem(job["source"]))
            self.table.setItem(row, 3, QTableWidgetItem(f"{job['score']:.3f}"))
            self.table.setItem(row, 4, QTableWidgetItem(job["url"]))


class CVTab(QWidget):
    def __init__(self, profile_tab: ProfileTab):
        super().__init__()
        self.profile_tab = profile_tab

        layout = QVBoxLayout()
        self.generate_btn = QPushButton("Generate CV (text)")
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        self.generate_btn.clicked.connect(self.generate_cv)

        layout.addWidget(self.generate_btn)
        layout.addWidget(self.output)
        self.setLayout(layout)

    def generate_cv(self):
        text = f"""
{self.profile_tab.role.text()}

Skills:
{self.profile_tab.skills.toPlainText()}

Summary:
{self.profile_tab.summary.toPlainText()}
"""
        self.output.setPlainText(text.strip())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Job Recommender & CV Generator")
        self.resize(1100, 700)

        tabs = QTabWidget()

        self.profile_tab = ProfileTab()
        self.jobs_tab = JobsTab(self.profile_tab)
        self.cv_tab = CVTab(self.profile_tab)

        tabs.addTab(self.profile_tab, "Profile")
        tabs.addTab(self.jobs_tab, "Jobs")
        tabs.addTab(self.cv_tab, "CV")

        self.setCentralWidget(tabs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
