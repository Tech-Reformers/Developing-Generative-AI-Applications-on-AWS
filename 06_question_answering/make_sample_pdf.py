"""Generate the sample PDF used by the question-answering demos.

We build a minimal, valid multi-line PDF by hand so the demo has no extra
dependencies (no reportlab). Run this once to (re)create sample_report.pdf.
"""

# Each string is one line of the report. The demo questions are answerable
# only from this content - that's the point of grounding the model in a doc.
LINES = [
    "Quantum Computing Industry Report - 2025",
    "",
    "Projected growth: the industry projected 4,200 logical qubits by 2026.",
    "Actual trajectory: as of 2025, deployments reached only 1,100 qubits,",
    "well below the projection - a shortfall of roughly 74 percent.",
    "",
    "Leading vendors: Aurora Quantum, Nimbus Systems, and Corewave Labs.",
    "Aurora Quantum holds the largest market share at 38 percent.",
    "",
    "Primary bottleneck: error-correction overhead, not raw qubit count.",
    "Analysts expect the projection gap to narrow after 2027.",
]

PAGE_HEIGHT = 792


def escape(text):
    return text.replace("(", r"\(").replace(")", r"\)")


def build_pdf():
    # Build the text-drawing content stream: one line per row, moving down.
    parts = ["BT", "/F1 12 Tf", "50 740 Td", "16 TL"]
    for i, line in enumerate(LINES):
        if i == 0:
            parts.append(f"({escape(line)}) Tj")
        else:
            parts.append("T*")
            parts.append(f"({escape(line)}) Tj")
    parts.append("ET")
    content = "\n".join(parts).encode()

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n"
        + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(pdf))
        pdf += str(i).encode() + b" 0 obj\n" + obj + b"\nendobj\n"

    xref_pos = len(pdf)
    pdf += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n"
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += ("%010d 00000 n \n" % off).encode()
    pdf += (b"trailer\n<< /Size " + str(len(objs) + 1).encode()
            + b" /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode()
            + b"\n%%EOF")
    return pdf


if __name__ == "__main__":
    with open("sample_report.pdf", "wb") as f:
        f.write(build_pdf())
    print("Wrote sample_report.pdf")
