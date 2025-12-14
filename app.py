import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget,
    QVBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, 
    QProgressBar, QScrollArea, QCheckBox, QGroupBox, QComboBox
)
from PySide6.QtCore import QThread, Signal, QUrl, Qt
from PySide6.QtGui import QDesktopServices
import os

from core.rag_engine import recommender
from core.cv_generator import generate_cv
from core.pdf_writer import generate_resume_pdf_from_text
from core.storage import save_profile, load_profile, list_profiles, save_cv_history

def make_scrollable(widget: QWidget) -> QWidget:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(widget)
    return scroll

class JobWorker(QThread):
    finished = Signal(object)

    def __init__(self, title: str, skills: str):
        super().__init__()
        self.title = title or ""
        self.skills = skills or ""

    def run(self):
        query = self.title or self.skills

        ok = recommender.ingest(query)
        if not ok:
            self.finished.emit([])
            return

        df = recommender.search(
            semantic_query=self.skills or self.title,
            top_k=30
        )
        self.finished.emit(df)


class CVWorker(QThread):
    finished = Signal(str, str)

    def __init__(self, profile: dict):
        super().__init__()
        self.profile = profile

    def run(self):
        raw_text = generate_cv(self.profile)

        output_path = "generated_resume.pdf"
        generate_resume_pdf_from_text(raw_text, self.profile, output_path)

        self.finished.emit(output_path, raw_text)



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
        self.full_name = QLineEdit()
        self.location = QLineEdit()
        self.email = QLineEdit()
        self.phone = QLineEdit()
        self.linkedin = QLineEdit()
        self.github = QLineEdit()
        self.degree = QLineEdit()
        self.university = QLineEdit()
        self.grad_year = QLineEdit()
        self.has_experience = QCheckBox("I have professional work experience")
        self.has_experience.setChecked(False)

        self.profile_selector = QComboBox()
        self.profile_selector.addItems(list_profiles())

        self.save_profile_btn = QPushButton("Save Profile")
        self.save_profile_btn.clicked.connect(self.save_current_profile)

        self.load_profile_btn = QPushButton("Load Profile")
        self.load_profile_btn.clicked.connect(self.load_selected_profile)

        layout.addWidget(QLabel("Saved Profiles"))
        layout.addWidget(self.profile_selector)
        layout.addWidget(self.save_profile_btn)
        layout.addWidget(self.load_profile_btn)


        layout.addWidget(QLabel("Full Name"))
        layout.addWidget(self.full_name)

        layout.addWidget(QLabel("Location (City, Country)"))
        layout.addWidget(self.location)

        layout.addWidget(QLabel("Email"))
        layout.addWidget(self.email)

        layout.addWidget(QLabel("Phone"))
        layout.addWidget(self.phone)

        layout.addWidget(QLabel("LinkedIn URL"))
        layout.addWidget(self.linkedin)

        layout.addWidget(QLabel("GitHub URL"))
        layout.addWidget(self.github)

        layout.addWidget(QLabel("Degree"))
        layout.addWidget(self.degree)

        layout.addWidget(QLabel("University"))
        layout.addWidget(self.university)

        layout.addWidget(QLabel("Graduation Year"))
        layout.addWidget(self.grad_year)

        layout.addWidget(self.has_experience)
        self.exp_group = QGroupBox("Professional Experience")
        self.exp_layout = QVBoxLayout()

        self.company = QLineEdit()
        self.job_title = QLineEdit()
        self.employment_type = QLineEdit()
        self.years = QLineEdit()

        self.exp_layout.addWidget(QLabel("Company"))
        self.exp_layout.addWidget(self.company)

        self.exp_layout.addWidget(QLabel("Position"))
        self.exp_layout.addWidget(self.job_title)

        self.exp_layout.addWidget(QLabel("Employment Type (e.g. Full-time, Internship)"))
        self.exp_layout.addWidget(self.employment_type)

        self.exp_layout.addWidget(QLabel("Years (e.g. 2023–2025)"))
        self.exp_layout.addWidget(self.years)

        self.exp_group.setLayout(self.exp_layout)
        self.exp_group.setVisible(False)

        layout.addWidget(self.exp_group)

        self.has_experience.toggled.connect(self.exp_group.setVisible)


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
            # ---------- PERSONAL INFO ----------
            "full_name": self.full_name.text().strip(),
            "location": self.location.text().strip(),
            "email": self.email.text().strip(),
            "phone": self.phone.text().strip(),
            "linkedin": self.linkedin.text().strip(),
            "github": self.github.text().strip(),

            # ---------- EDUCATION ----------
            "education": {
                "degree": self.degree.text().strip(),
                "university": self.university.text().strip(),
                "year": self.grad_year.text().strip(),
            },

            # ---------- FLAGS ----------
            "has_experience": self.has_experience.isChecked(),

            "profile_experience": {
                "company": self.company.text().strip(),
                "position": self.job_title.text().strip(),
                "type": self.employment_type.text().strip(),
                "years": self.years.text().strip(),
            } if self.has_experience.isChecked() else None,

            # --- MODEL INPUT ---
            "position": self.position.text().strip(),
            "skills": self.skills.toPlainText().strip(),
            "summary": self.summary.toPlainText().strip(),
            "looking_for": self.looking_for.toPlainText().strip(),
            "highlights": self.highlights.toPlainText().strip(),
            "primary_keyword": self.primary_keyword.text().strip(),
        }

    def save_current_profile(self):
        name = self.position.text().strip().lower().replace(" ", "_") or "default"
        save_profile(name, self.get_profile())
        self.profile_selector.clear()
        self.profile_selector.addItems(list_profiles())


    def load_selected_profile(self):
        name = self.profile_selector.currentText()
        if not name:
            return
        data = load_profile(name)
        self.populate_profile(data)

    def populate_profile(self, profile: dict):
        self.full_name.setText(profile.get("full_name", ""))
        self.location.setText(profile.get("location", ""))
        self.email.setText(profile.get("email", ""))
        self.phone.setText(profile.get("phone", ""))
        self.linkedin.setText(profile.get("linkedin", ""))
        self.github.setText(profile.get("github", ""))

        edu = profile.get("education", {})
        self.degree.setText(edu.get("degree", ""))
        self.university.setText(edu.get("university", ""))
        self.grad_year.setText(edu.get("year", ""))

        self.position.setText(profile.get("position", ""))
        self.skills.setPlainText(profile.get("skills", ""))
        self.summary.setPlainText(profile.get("summary", ""))
        self.looking_for.setPlainText(profile.get("looking_for", ""))
        self.highlights.setPlainText(profile.get("highlights", ""))
        self.primary_keyword.setText(profile.get("primary_keyword", ""))

        has_exp = profile.get("has_experience", False)
        self.has_experience.setChecked(has_exp)
        self.exp_group.setVisible(has_exp)

        exp = profile.get("profile_experience") or {}
        self.company.setText(exp.get("company", ""))
        self.job_title.setText(exp.get("position", ""))
        self.employment_type.setText(exp.get("type", ""))
        self.years.setText(exp.get("years", ""))

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
    def __init__(self, profile_tab):
        super().__init__()
        self.profile_tab = profile_tab
        self.pdf_path = None

        layout = QVBoxLayout()

        self.generate_btn = QPushButton("Generate CV (PDF)")
        self.status = QLabel("")
        self.status.setWordWrap(True)

        self.path_label = QLabel("")
        self.path_label.setOpenExternalLinks(False)
        self.path_label.setTextInteractionFlags(
            self.path_label.textInteractionFlags() | 
            Qt.TextSelectableByMouse
        )

        self.raw_preview = QTextEdit()
        self.raw_preview.setReadOnly(False)
        self.raw_preview.setPlaceholderText("Raw model output will appear here…")

        layout.addWidget(QLabel("Model Output (Debug)"))
        layout.addWidget(self.raw_preview)

        self.recompile_btn = QPushButton("Recompile PDF from Edited Text")
        self.recompile_btn.setEnabled(False)
        self.recompile_btn.clicked.connect(self.recompile_pdf)

        layout.addWidget(self.recompile_btn)


        self.open_btn = QPushButton("Open PDF")
        self.folder_btn = QPushButton("Show in Folder")

        self.open_btn.setEnabled(False)
        self.folder_btn.setEnabled(False)

        self.generate_btn.clicked.connect(self.generate)
        self.open_btn.clicked.connect(self.open_pdf)
        self.folder_btn.clicked.connect(self.open_folder)

        layout.addWidget(self.generate_btn)
        layout.addWidget(self.status)
        layout.addWidget(self.path_label)
        layout.addWidget(self.open_btn)
        layout.addWidget(self.folder_btn)

        self.setLayout(layout)

    def generate(self):
        profile = self.profile_tab.get_profile()

        self.status.setText("Generating CV PDF… please wait")
        self.path_label.setText("")
        self.generate_btn.setEnabled(False)
        self.open_btn.setEnabled(False)
        self.folder_btn.setEnabled(False)

        self.worker = CVWorker(profile)
        self.worker.finished.connect(self.on_result_ready)
        self.worker.start()

    def on_result_ready(self, pdf_path: str, raw_text: str):
        self.pdf_path = os.path.abspath(pdf_path)

        self.status.setText("CV generated successfully ✔")
        self.path_label.setText(f"<b>Saved to:</b><br>{self.pdf_path}")
        self.raw_preview.setPlainText(raw_text)

        self.generate_btn.setEnabled(True)
        self.open_btn.setEnabled(True)
        self.folder_btn.setEnabled(True)
        self.recompile_btn.setEnabled(True)

        save_cv_history(
            profile_name=self.profile_tab.position.text() or "default",
            raw_text=raw_text
        )

    def recompile_pdf(self):
        edited_text = self.raw_preview.toPlainText().strip()
        if not edited_text:
            self.status.setText("Cannot recompile: raw text is empty")
            return

        self.status.setText("Recompiling PDF from edited text…")

        output_path = "generated_resume.pdf"

        generate_resume_pdf_from_text(
            edited_text,
            self.profile_tab.get_profile(),
            output_path
        )

        self.pdf_path = os.path.abspath(output_path)
        self.status.setText("PDF recompiled successfully")
        self.path_label.setText(f"<b>Saved to:</b><br>{self.pdf_path}")

        self.open_btn.setEnabled(True)
        self.folder_btn.setEnabled(True)

    def open_pdf(self):
        if self.pdf_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.pdf_path))

    def open_folder(self):
        if self.pdf_path:
            folder = os.path.dirname(self.pdf_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Job Recommender & CV Generator")
        self.resize(1100, 700)

        tabs = QTabWidget()

        self.profile_tab = ProfileTab()
        self.jobs_tab = JobsTab(self.profile_tab)
        self.cv_tab = CVTab(self.profile_tab)

        tabs.addTab(make_scrollable(self.profile_tab), "Profile")
        tabs.addTab(make_scrollable(self.jobs_tab), "Jobs")
        tabs.addTab(make_scrollable(self.cv_tab), "CV")

        self.setCentralWidget(tabs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
