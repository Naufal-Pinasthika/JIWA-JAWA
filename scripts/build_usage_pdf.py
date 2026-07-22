from __future__ import annotations

from pathlib import Path


def main() -> int:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
    except Exception as exc:  # noqa: BLE001
        print(f"ReportLab is required to build docs/USAGE.pdf: {exc}")
        return 2

    source = Path("docs/USAGE.md")
    target = Path("docs/USAGE.pdf")
    styles = getSampleStyleSheet()
    story = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            story.append(Paragraph(line[2:], styles["Title"]))
            story.append(Spacer(1, 12))
        elif line.startswith("## "):
            story.append(PageBreak())
            story.append(Paragraph(line[3:], styles["Heading1"]))
        elif line.startswith("### "):
            story.append(Paragraph(line[4:], styles["Heading2"]))
        elif line.startswith("- "):
            story.append(Paragraph("&bull; " + line[2:], styles["BodyText"]))
        elif line.strip() == "":
            story.append(Spacer(1, 8))
        else:
            story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), styles["BodyText"]))
    target.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(target), pagesize=A4, title="Catur Jawa Usage Guide").build(story)
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
