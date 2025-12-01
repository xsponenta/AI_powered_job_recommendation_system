import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget,
    QVBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QProgressBar
)
from PySide6.QtCore import QThread, Signal

from core.job_recommender import recommend_jobs
from core.cv_generator import generate_cv


class JobWorker(QThread):
    finished = Signal(object)

    def __init__(self, title: str, skills: str):
        super().__init__()
        self.title = title or ""
        self.skills = skills or ""

    def run(self):
        df = recommend_jobs(
            title=self.title,
            skills=self.skills
        )
        self.finished.emit(df)


class CVWorker(QThread):
    finished = Signal(str)

    def __init__(self, profile: dict):
        super().__init__()
        self.profile = profile

    def run(self):
        text = generate_cv(self.profile)
        self.finished.emit(text)


class ProfileTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.position = QLineEdit()
        self.skills = QTextEdit()
        self.summary = QTextEdit()
        self.looking_for = QTextEdit()
        self.highlights = QTextEdit()
        self.primary_keyword = QLineEdit()

        layout.addWidget(QLabel("Target Role"))
        layout.addWidget(self.position)

        layout.addWidget(QLabel("Skills (comma separated)"))
        layout.addWidget(self.skills)

        layout.addWidget(QLabel("More info / Summary"))
        layout.addWidget(self.summary)

        layout.addWidget(QLabel("Looking For"))
        layout.addWidget(self.looking_for)

        layout.addWidget(QLabel("Highlights"))
        layout.addWidget(self.highlights)

        layout.addWidget(QLabel("Primary Keyword"))
        layout.addWidget(self.primary_keyword)

        self.setLayout(layout)

    def get_profile(self) -> dict:
        return {
            "position": self.position.text().strip(),
            "skills": self.skills.toPlainText().strip(),
            "summary": self.summary.toPlainText().strip(),
            "looking_for": self.looking_for.toPlainText().strip(),
            "highlights": self.highlights.toPlainText().strip(),
            "primary_keyword": self.primary_keyword.text().strip(),
        }

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
            ["Title", "Company", "Source", "Match %", "URL"]
        )

        self.fetch_btn.clicked.connect(self.fetch_jobs)

        layout.addWidget(self.fetch_btn)
        layout.addWidget(self.progress)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def build_job_query_from_profile(self, profile: dict) -> dict:
        """
        Builds queries for job fetching & ranking
        from all profile fields.
        """

        title = profile.get("position", "").strip()

        # Everything else contributes to semantic matching
        semantic_parts = [
            profile.get("skills", ""),
            profile.get("summary", ""),
            profile.get("looking_for", ""),
            profile.get("highlights", ""),
            profile.get("primary_keyword", ""),
        ]

        semantic_query = " ".join(p for p in semantic_parts if p).strip()

        return {
            "title": title,
            "semantic": semantic_query,
        }


    def fetch_jobs(self):
        profile = self.profile_tab.get_profile()

        queries = self.build_job_query_from_profile(profile)
        title = queries["title"]
        semantic = queries["semantic"]

        if not title and not semantic:
            return

        self.progress.show()

        self.worker = JobWorker(
            title=title,
            skills=semantic   # semantic context goes here
        )
        self.worker.finished.connect(self.display_jobs)
        self.worker.start()


    def display_jobs(self, df):
        self.progress.hide()
        self.table.setRowCount(len(df))

        for row, (_, job) in enumerate(df.iterrows()):
            self.table.setItem(row, 0, QTableWidgetItem(job["title"]))
            self.table.setItem(row, 1, QTableWidgetItem(job["company"]))
            self.table.setItem(row, 2, QTableWidgetItem(job["source"]))
            self.table.setItem(row, 3, QTableWidgetItem(f"{job['score']:.1f}%"))
            self.table.setItem(row, 4, QTableWidgetItem(job["url"]))

class CVTab(QWidget):
    def __init__(self, profile_tab: ProfileTab):
        super().__init__()
        self.profile_tab = profile_tab

        layout = QVBoxLayout()

        self.generate_btn = QPushButton("Generate CV")
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        self.generate_btn.clicked.connect(self.generate)

        layout.addWidget(self.generate_btn)
        layout.addWidget(self.output)
        self.setLayout(layout)

    def generate(self):
        profile = self.profile_tab.get_profile()

        self.output.setPlainText("Generating CV… please wait")
        self.worker = CVWorker(profile)
        self.worker.finished.connect(self.output.setPlainText)
        self.worker.start()

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
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
