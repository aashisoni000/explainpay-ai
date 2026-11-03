import io
import json
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.schemas import InvestigationDetail


def generate_pdf(investigation: InvestigationDetail) -> bytes:
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    story = []

    def paragraph(text: object, style: str = "BodyText") -> None:
        # Paragraph uses XML markup; evidence must always be text, not markup.
        story.append(Paragraph(escape(str(text)), styles[style]))
        story.append(Spacer(1, 0.06 * inch))

    paragraph("ExplainPay investigation report", "Title")
    paragraph(investigation.title, "Heading2")
    paragraph(f"Investigation: {investigation.id}")
    paragraph(f"Created (UTC): {investigation.created_at.isoformat()}")
    paragraph(f"Status: {investigation.status}; risk: {investigation.risk_level or 'not assessed'}")
    paragraph(
        "Academic decision-support evidence, not a financial or security guarantee. "
        "Model probabilities are estimates. Provider unavailability is not evidence of safety."
    )
    paragraph(
        "SHAP contributions and explanation base values are in log-odds units, "
        "not probability units. Their sum is the model's predicted log-odds."
    )
    if investigation.upload is not None:
        upload = investigation.upload
        paragraph("Transaction batch", "Heading2")
        paragraph(f"File: {upload.filename}")
        paragraph(f"Processed: {upload.processed_records} of {upload.total_records}")
        paragraph(
            f"Flagged: {upload.summary.flagged}; legitimate predictions: "
            f"{upload.summary.legitimate}; high risk: {upload.summary.high_risk}"
        )
        if not upload.results:
            paragraph("This upload has not been analyzed. No predictions are available.")
        transactions = upload.results
    else:
        transactions = [investigation.transaction] if investigation.transaction is not None else []
    for result in transactions:
        paragraph(f"Transaction {result.transaction_reference}", "Heading3")
        paragraph(
            f"Amount: {result.amount:g}; fraud probability: {result.fraud_probability:.6f}; "
            f"prediction: {result.prediction}; threshold: {result.threshold:g}; "
            f"risk: {result.risk_level}"
        )
        paragraph(f"Model: {result.model_version}; explanation base value: {result.base_value:g}")
        paragraph(f"Anomaly score: {result.anomaly_score}; anomaly flag: {result.is_anomaly}")
        if result.merchant_url:
            paragraph(f"Merchant URL (not fetched): {result.merchant_url}")
        for item in result.explanation:
            paragraph(
                f"{item.feature}: value={item.value:g}, SHAP contribution={item.contribution:.6g}"
            )
    if investigation.website is not None:
        scan = investigation.website
        paragraph("Website evidence", "Heading2")
        paragraph(f"URL (not fetched): {scan.url}")
        paragraph(f"Domain: {scan.normalized_domain}")
        paragraph(
            f"Phishing probability: {scan.ml_probability:.6f}; prediction: {scan.ml_prediction}; "
            f"threshold: {scan.threshold:g}; risk: {scan.risk_level}; model: {scan.model_version}"
        )
        if scan.base_value is not None:
            paragraph(f"Explanation base value: {scan.base_value:g}")
        for item in scan.explanation:
            paragraph(
                f"{item.feature}: value={item.value:g}, SHAP contribution={item.contribution:.6g}"
            )
        paragraph("Extracted lexical features", "Heading3")
        for name, value in scan.features.items():
            paragraph(f"{name}: {value:g}")
        for provider in scan.providers:
            paragraph(f"Provider {provider.name}: {provider.status}")
            paragraph(json.dumps(provider.details, ensure_ascii=True, sort_keys=True))
        for finding in scan.findings:
            paragraph(f"{finding.source}: {finding.severity} — {finding.description}")
            paragraph(json.dumps(finding.evidence, ensure_ascii=True, sort_keys=True))

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFillColor(colors.grey)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(inch, 0.5 * inch, f"ExplainPay | Page {doc.page}")
        canvas.restoreState()

    SimpleDocTemplate(
        buffer,
        title="ExplainPay investigation evidence",
        author="ExplainPay",
        leftMargin=inch,
        rightMargin=inch,
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
