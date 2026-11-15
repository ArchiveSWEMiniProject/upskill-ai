"""Rebuild stc_f1_01_resume.docx, the resume used by STC-F1-01.

Run from the repository root:

    python docs/testing/fixtures/make_stc_f1_01_resume.py

The text is chosen so the extractor (backend/profile/skill_extraction.py)
proposes exactly three skills with known levels and confidences; see
docs/testing/STC-F1-01.md, step 6. Change it only together with that table.
"""

from pathlib import Path

from docx import Document

LINES = [
    "Asha Rao",
    "B.Tech Computer Science, PES University, 2027",
    "Technical skills: Python at an intermediate level.",
    "Built a timetable planner in Python that reads course data from CSV files.",
    "Comfortable writing SQL queries for coursework.",
    "Currently learning Docker for packaging small apps.",
]

OUT = Path(__file__).with_name("stc_f1_01_resume.docx")


def main() -> None:
    document = Document()
    for line in LINES:
        document.add_paragraph(line)
    document.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
