import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from .models import SessionSummary

def generate_session_pdf(session, feedback):
    """
    Generates a PDF report for a session and returns it as a bytes buffer.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center
    subtitle_style = styles['Heading3']
    subtitle_style.alignment = 1 # Center
    subtitle_style.textColor = colors.HexColor('#475569')
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    normal_style.leading = 14
    bold_style = ParagraphStyle('Bold', parent=normal_style, fontName='Helvetica-Bold')

    # Title
    story.append(Paragraph(f"SmartClass AI - Session Report", title_style))
    story.append(Paragraph(f"{session.label or f'Session #{session.id}'}", subtitle_style))
    story.append(Spacer(1, 20))

    # Summary Text
    if feedback and feedback.overall_summary:
        story.append(Paragraph("OVERALL SUMMARY", styles['Heading4']))
        for line in feedback.overall_summary.split('\n'):
            if line.strip():
                story.append(Paragraph(line.strip(), normal_style))
                story.append(Spacer(1, 4))
        story.append(Spacer(1, 10))
    
    if feedback and feedback.recommendations:
        story.append(Paragraph("RECOMMENDATIONS", styles['Heading4']))
        for line in feedback.recommendations.split('\n'):
            if line.strip():
                story.append(Paragraph(line.strip(), normal_style))
                story.append(Spacer(1, 4))
        story.append(Spacer(1, 20))

    # Student Table
    summaries = SessionSummary.objects.filter(session=session).select_related('student').order_by('-avg_score')
    if summaries.exists():
        story.append(Paragraph("PER-STUDENT RESULTS", styles['Heading4']))
        story.append(Spacer(1, 10))
        
        # Table Header
        data = [['Student', 'USN', 'Score', 'Grade', 'Attentive %', 'Distracted %', 'Phone']]
        for s in summaries:
            data.append([
                s.student.name or 'Unknown',
                s.student.usn or '-',
                f"{round(s.avg_score * 100, 1)}%",
                s.grade,
                f"{s.attentive_pct}%",
                f"{s.distracted_pct}%",
                str(s.phone_frames)
            ])
        
        table = Table(data, colWidths=[120, 80, 50, 50, 70, 75, 50])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (1, -1), 'LEFT'), # Left align names and USNs
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#0f172a')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        story.append(table)

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
