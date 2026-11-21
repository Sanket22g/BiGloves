import os
import urllib.parse
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls
from docx.opc.constants import RELATIONSHIP_TYPE

# -------------------------------------------------------------
# XML & Styling Helpers
# -------------------------------------------------------------
def set_cell_background(cell, hex_color):
    """Sets background color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    for shd in tcPr.findall(qn('w:shd')):
        tcPr.remove(shd)
    new_shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(new_shd)

def set_cell_margins(cell, top=100, bottom=100, left=120, right=120):
    """Sets inner margins (padding) of a cell in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders(table, color="D1D5DB", sz="4", val="single"):
    """Applies clean, subtle borders across all cells in table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def make_row_header(row):
    """Marks a row as repeating table header on every page."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))

def prevent_row_split(row):
    """Prevents a table row from splitting across pages."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))

def add_hyperlink(paragraph, url, text, color="1D4ED8", underline=True, bold=False, font_size=None, font_name="Calibri"):
    """Adds a clickable hyperlink to a paragraph."""
    if not url:
        run = paragraph.add_run(text)
        if font_size:
            run.font.size = Pt(font_size)
        if font_name:
            run.font.name = font_name
        return run

    part = paragraph.part
    r_id = part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)

    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)

    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')

    if font_name:
        rFonts = OxmlElement('w:rFonts')
        rFonts.set(qn('w:ascii'), font_name)
        rFonts.set(qn('w:hAnsi'), font_name)
        rPr.append(rFonts)

    if color:
        c = OxmlElement('w:color')
        c.set(qn('w:val'), color)
        rPr.append(c)

    if underline:
        u = OxmlElement('w:u')
        u.set(qn('w:val'), 'single')
        rPr.append(u)

    if bold:
        b = OxmlElement('w:b')
        rPr.append(b)

    if font_size:
        sz = OxmlElement('w:sz')
        sz.set(qn('w:val'), str(int(font_size * 2)))
        rPr.append(sz)

    new_run.append(rPr)
    new_run.text = text
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink


# -------------------------------------------------------------
# Raw Data
# -------------------------------------------------------------
rows = [
    ("Manus AI","GenAI / AI agents","~167","Active","10/10"),
    ("OneByZero","Enterprise GenAI / AI agents / AWS","~135","Active","10/10"),
    ("Level3AI","AI agents / CX / AgentOps","<100","Growing","10/10"),
    ("Acrab","Edge AI / AI compute / chips","~50–200","Growing","10/10"),
    ("Video Rebirth","Generative video / foundation models","~37","Growing","10/10"),
    ("Ropedia","Physical AI / robotics data","11–50","Growing","10/10"),
    ("Sharpa","AI robotics / embodied AI","~70","Hiring signal","10/10"),
    ("Dyna.Ai","Enterprise AI / GenAI","~115","Growing","9.5/10"),
    ("Whale","Enterprise AI / agents / vision","~103","Growing","9.5/10"),
    ("Wubble","Generative AI / audio","~11","Startup / outreach","9.5/10"),
    ("Ailytics","Computer vision / video analytics","~53","Active signal","9.5/10"),
    ("H3 Zoom","Computer vision / robotics / inspection","11–50","Growing","9.5/10"),
    ("SixSense","Semiconductor AI / computer vision","~75","Growing","9.5/10"),
    ("Augmentus","Robotics / AI / robot programming","~30–50","Hiring signal","9.5/10"),
    ("Eureka Robotics","Robotics / AI / manipulation","50+","Growing","9.5/10"),
    ("Botsync","Robotics / deep learning / autonomous systems","50–200","Signal","9/10"),
    ("AI Rudder","Voice AI / NLP","~300","Signal","9/10"),
    ("WIZ.AI","Voice AI / conversational AI","100+","Growing","9/10"),
    ("SleekFlow","AI agents / conversational commerce","~200","Growing","9/10"),
    ("Hypotenuse AI","LLM / AI agents / ecommerce","11–50","Signal","9/10"),
    ("fileAI","Agentic AI / document intelligence","50–200","Growing","9/10"),
    ("Betterdata","Synthetic data / AI research","11–50","Hiring signal","9/10"),
    ("Tookitaki","AI / AML / agentic AI","~130","Signal","9/10"),
    ("Silent Eight","AI / financial crime / NLP","~109","Signal","9/10"),
    ("NextBillion.ai","AI optimization / routing","~70","Signal","8.5/10"),
    ("CloudSEK","AI cybersecurity / ML","~247","Signal","8.5/10"),
    ("PatSnap","AI agents / knowledge intelligence","~596","Signal","8.5/10"),
    ("ViSenze","Computer vision / visual search","~40","Signal","8.5/10"),
    ("TAIGER","NLP / semantic AI","~80","Outreach","8.5/10"),
    ("Sentient.io","NLP / speech / computer vision","~14","Outreach","8.5/10"),
    ("Bot MD","Healthcare AI agents","~28","Signal","8.5/10"),
    ("Crayon Data","AI / data / personalization","~134","Signal","8/10"),
    ("Cerebry","AI education / ML","~104","Outreach","8/10"),
    ("X0PA AI","Recruitment AI / NLP","~67","Signal","8/10"),
    ("Pulsifi","HR AI / predictive analytics","~68","Outreach","8/10"),
    ("Ai Palette","NLP / predictive AI / GenAI","~66","Outreach","8/10"),
    ("Advance.AI","ML / fintech / risk AI","~347","Signal","8/10"),
    ("SQREEM Technologies","AI analytics / big data","~122","Outreach","8/10"),
    ("Impress.ai","Conversational AI / recruitment","~69","Signal","8/10"),
    ("RegASK","AI / regulatory intelligence","~83","Outreach","7.5/10"),
    ("Engine Biosciences","AI drug discovery","~36","Signal","7.5/10"),
    ("Gero","AI drug discovery / longevity","50+","Signal","7.5/10"),
    ("Respiree","Healthcare AI / ML","50+","Signal","7.5/10"),
    ("Holmusk","Health data / AI analytics","~88","Signal","7.5/10"),
    ("TopView AI","Generative video / AI advertising","100+","Growing","7.5/10"),
    ("Graas","Ecommerce AI / analytics","100+","Growing","7.5/10"),
    ("Lev8","AI prospecting agents","<50","Growing","9/10"),
    ("Sapient","Reasoning models / LLM","<50","Growing","10/10"),
    ("Galatek","AI lab automation / robotics","<100","Growing","9/10"),
    ("Transparently.AI","AI accounting / forensic analysis","<50","Signal","8/10"),
]

company_links = {
    "Manus AI":"https://www.linkedin.com/company/manus-im/",
    "OneByZero":"https://www.linkedin.com/company/1bz/",
    "Level3AI":"https://www.linkedin.com/search/results/companies/?keywords=Level3AI%20Singapore",
    "Acrab":"https://www.linkedin.com/company/acrabai/",
    "Video Rebirth":"https://www.linkedin.com/company/video-rebirth/",
    "Ropedia":"https://www.linkedin.com/company/ropedia/",
    "Sharpa":"https://www.linkedin.com/company/sharpa-robotics/",
    "Dyna.Ai":"https://www.linkedin.com/company/dyna-ai/",
    "Whale":"https://www.linkedin.com/company/whale-inc/",
    "Wubble":"https://www.linkedin.com/company/wubble-ai/",
    "Ailytics":"https://www.linkedin.com/company/ailytics/",
    "H3 Zoom":"https://sg.linkedin.com/company/h3zoom/",
    "SixSense":"https://sg.linkedin.com/company/sixsenseai/",
    "Augmentus":"https://www.linkedin.com/company/augmentus/",
    "Eureka Robotics":"https://www.linkedin.com/company/eureka-robotics/",
    "Botsync":"https://www.linkedin.com/company/botsync/",
    "AI Rudder":"https://www.linkedin.com/company/ai-rudder/",
    "WIZ.AI":"https://www.linkedin.com/company/wiz-ai/",
    "SleekFlow":"https://www.linkedin.com/company/sleekflow/",
    "Hypotenuse AI":"https://sg.linkedin.com/company/hypotenuse-ai",
    "fileAI":"https://www.linkedin.com/company/fileai/",
    "Betterdata":"https://sg.linkedin.com/company/betterdataai/",
    "Tookitaki":"https://www.linkedin.com/company/tookitaki/",
    "Silent Eight":"https://www.linkedin.com/company/silent-eight/",
    "NextBillion.ai":"https://sg.linkedin.com/company/nextbillion-ai/",
    "CloudSEK":"https://www.linkedin.com/company/cloudsek/",
    "PatSnap":"https://www.linkedin.com/company/patsnap/",
    "ViSenze":"https://www.linkedin.com/company/visenze/",
    "TAIGER":"https://www.linkedin.com/company/taiger/",
    "Sentient.io":"https://www.linkedin.com/company/sentientio/",
    "Bot MD":"https://www.linkedin.com/company/bot-md/",
    "Crayon Data":"https://www.linkedin.com/company/crayon-data/",
    "Cerebry":"https://www.linkedin.com/company/cerebry/",
    "X0PA AI":"https://www.linkedin.com/company/x0pa-ai/",
    "Pulsifi":"https://www.linkedin.com/company/pulsifi/",
    "Ai Palette":"https://www.linkedin.com/company/ai-palette/",
    "Advance.AI":"https://www.linkedin.com/company/advanceai/",
    "SQREEM Technologies":"https://www.linkedin.com/company/sqreem-technologies/",
    "Impress.ai":"https://www.linkedin.com/company/impress-ai/",
    "RegASK":"https://www.linkedin.com/company/regask/",
    "Engine Biosciences":"https://www.linkedin.com/company/engine-biosciences/",
    "Gero":"https://www.linkedin.com/company/gero/",
    "Respiree":"https://www.linkedin.com/company/respiree/",
    "Holmusk":"https://sg.linkedin.com/company/holmusk",
    "TopView AI":"https://www.linkedin.com/company/topviewai/",
    "Graas":"https://www.linkedin.com/company/graas-ai/",
    "Lev8":"https://www.linkedin.com/company/lev8-ai/",
    "Sapient":"https://www.linkedin.com/company/sapient-ai/",
    "Galatek":"https://www.linkedin.com/company/galatek-ai/",
    "Transparently.AI":"https://www.linkedin.com/company/transparently-ai/",
}

website = {
    "Manus AI":"https://manus.im/",
    "OneByZero":"https://www.onebyzero.ai/",
    "Level3AI":"https://level3.ai/",
    "Acrab":"https://www.acrab.ai/",
    "Video Rebirth":"https://videorebirth.com/",
    "Ropedia":"https://ropedia.com/",
    "Sharpa":"https://www.sharpa.com/",
    "Dyna.Ai":"https://dyna.ai/",
    "Whale":"https://www.whale.im/",
    "Wubble":"https://wubble.ai/",
    "Ailytics":"https://ailytics.ai/",
    "H3 Zoom":"http://www.h3zoom.ai",
    "SixSense":"https://www.sixsense.ai/",
    "Augmentus":"https://www.augmentus.tech/",
    "Eureka Robotics":"https://eureka-robotics.com/",
    "Botsync":"https://www.botsync.co/",
    "AI Rudder":"https://airudder.com/",
    "WIZ.AI":"https://www.wiz.ai/",
    "SleekFlow":"https://sleekflow.io/",
    "Hypotenuse AI":"https://hypotenuse.ai/",
    "fileAI":"https://fileai.com/",
    "Betterdata":"https://www.betterdata.ai/",
    "Tookitaki":"https://www.tookitaki.com/",
    "Silent Eight":"https://www.silenteight.com/",
    "NextBillion.ai":"https://nextbillion.ai/",
    "CloudSEK":"https://www.cloudsek.com/",
    "PatSnap":"https://www.patsnap.com/",
    "ViSenze":"https://www.visenze.com/",
    "TAIGER":"https://www.taiger.com/",
    "Sentient.io":"http://www.sentient.io",
    "Bot MD":"https://www.botmd.io/",
    "Crayon Data":"https://www.crayondata.com/",
    "Cerebry":"https://cerebry.co/",
    "X0PA AI":"https://x0pa.com/",
    "Pulsifi":"https://pulsifi.me/",
    "Ai Palette":"https://www.aipalette.com/",
    "Advance.AI":"https://www.advance.ai/",
    "SQREEM Technologies":"https://sqreemtech.com/",
    "Impress.ai":"https://impress.ai/",
    "RegASK":"https://regask.com/",
    "Engine Biosciences":"https://www.enginebio.com/",
    "Gero":"https://gero.ai/",
    "Respiree":"https://www.respiree.com/",
    "Holmusk":"https://www.holmusk.com/",
    "TopView AI":"https://www.topview.ai/",
    "Graas":"https://www.graas.ai/",
    "Lev8":"https://lev8.ai/",
    "Sapient":"https://sapient.io/",
    "Galatek":"https://galatek.ai/",
    "Transparently.AI":"https://transparently.ai/"
}

pipeline_stages = [
    ("Stage 1: Not Contacted", "Find Founder/CTO/Head of AI on LinkedIn, identify key tech stack, and personalize message angle.", "Preparation", "Before outreach"),
    ("Stage 2: Connection Sent", "Send a concise, personalized connection note (under 300 characters) highlighting mutual AI interests.", "LinkedIn Invite", "Day 1"),
    ("Stage 3: Connected", "Send a tailored internship value proposition pitch message within 24 hours of connection acceptance.", "First Message", "Within 24h"),
    ("Stage 4: Message Sent", "Log date contacted and allow 4 to 5 business days for review without premature follow-up.", "Waiting Period", "4–5 days"),
    ("Stage 5: Follow-up", "Send a polite, value-adding follow-up message referencing a relevant company project or GitHub repository.", "Follow-up", "Day 6–7"),
    ("Stage 6: Replied", "Acknowledge promptly within 2–4 hours; transition conversation to an exploratory call or direct email.", "Qualification", "Same day"),
    ("Stage 7: Interview", "Prepare company-specific code examples, portfolio review, and research their recent AI/product release.", "Evaluation", "Scheduled"),
    ("Stage 8: Offer / Closed", "Confirm terms, start date, work pass/internship criteria, and send formal acceptance.", "Closing", "Final Stage")
]

# -------------------------------------------------------------
# Document Generation
# -------------------------------------------------------------
def build_outreach_document(output_path):
    doc = docx.Document()

    # Configure Landscape Page Setup (11 x 8.5 in) with 0.5 in margins
    section = doc.sections[0]
    section.page_width = Inches(11.0)
    section.page_height = Inches(8.5)
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)
    section.top_margin = Inches(0.5)
    section.bottom_margin = Inches(0.5)

    # Base Styles
    styles = doc.styles
    normal_style = styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(9.5)
    normal_style.font.color.rgb = RGBColor(30, 41, 59) # Slate 800

    # ---------------------------------------------------------
    # 1. Header & Title Block
    # ---------------------------------------------------------
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(2)
    run_title = title_p.add_run("Singapore AI / ML Startup Outreach Directory & Tracker")
    run_title.font.name = 'Calibri'
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(15, 23, 42) # Slate 900

    subtitle_p = doc.add_paragraph()
    subtitle_p.paragraph_format.space_before = Pt(0)
    subtitle_p.paragraph_format.space_after = Pt(8)
    run_sub = subtitle_p.add_run("Comprehensive 50-Company Strategy Guide & Pipeline Tracker for AI/ML, GenAI, and Robotics Internships")
    run_sub.font.name = 'Calibri'
    run_sub.font.size = Pt(11)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(71, 85, 105) # Slate 600

    # Key Metadata Summary Callout Box (Table)
    meta_table = doc.add_table(rows=1, cols=4)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(meta_table, color="CBD5E1", sz="6", val="single")

    meta_items = [
        ("Target Roles", "AI/ML Intern | GenAI Intern\nMLOps | Robotics AI Intern"),
        ("Ecosystem", "Singapore Tech Ecosystem\n50 High-Growth AI Startups"),
        ("Primary Outreach", "LinkedIn Direct & InMail\nPersonalized Value Pitch"),
        ("Priority Tiers", "8 Tier-1 (10/10) | 8 Tier-2 (9.5/10)\n15 Tier-3 (9.0/10) | 19 High-Potential")
    ]

    for col_idx, (m_label, m_val) in enumerate(meta_items):
        cell = meta_table.cell(0, col_idx)
        set_cell_background(cell, "F1F5F9")
        set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2)
        r_lbl = p.add_run(m_label.upper() + "\n")
        r_lbl.font.size = Pt(8)
        r_lbl.font.bold = True
        r_lbl.font.color.rgb = RGBColor(30, 58, 138) # Dark Blue

        r_val = p.add_run(m_val)
        r_val.font.size = Pt(8.5)
        r_val.font.color.rgb = RGBColor(30, 41, 59)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ---------------------------------------------------------
    # 2. Section 1: Outreach Pipeline Stages & Playbook
    # ---------------------------------------------------------
    h1 = doc.add_paragraph()
    h1.paragraph_format.space_before = Pt(10)
    h1.paragraph_format.space_after = Pt(4)
    r_h1 = h1.add_run("1. Outreach Pipeline Workflow & Guidance")
    r_h1.font.size = Pt(13)
    r_h1.font.bold = True
    r_h1.font.color.rgb = RGBColor(30, 58, 138)

    guide_table = doc.add_table(rows=len(pipeline_stages) + 1, cols=4)
    guide_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(guide_table, color="E2E8F0", sz="4")

    # Guide headers
    guide_cols = ["Pipeline Stage", "Recommended Action / Best Practice", "Outreach Channel", "Standard Cadence"]
    guide_widths = [Inches(1.8), Inches(5.4), Inches(1.4), Inches(1.4)]
    
    header_row = guide_table.rows[0]
    make_row_header(header_row)
    prevent_row_split(header_row)

    for i, col_name in enumerate(guide_cols):
        cell = header_row.cells[i]
        set_cell_background(cell, "1E293B") # Dark slate
        set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(col_name)
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    for r_idx, (stg, act, chn, cad) in enumerate(pipeline_stages, start=1):
        row = guide_table.rows[r_idx]
        prevent_row_split(row)
        bg = "FFFFFF" if r_idx % 2 != 0 else "F8FAFC"
        
        for c_idx, text_val in enumerate([stg, act, chn, cad]):
            cell = row.cells[c_idx]
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(text_val)
            r.font.size = Pt(8.5)
            if c_idx == 0:
                r.font.bold = True
                r.font.color.rgb = RGBColor(15, 23, 42)
            elif c_idx == 3:
                r.font.color.rgb = RGBColor(37, 99, 235)
                r.font.bold = True

    # Apply widths
    for row in guide_table.rows:
        for i, w in enumerate(guide_widths):
            row.cells[i].width = w

    doc.add_page_break()

    # ---------------------------------------------------------
    # 3. Section 2: Master 50 Startup Outreach Directory Table
    # ---------------------------------------------------------
    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(0)
    h2.paragraph_format.space_after = Pt(3)
    r_h2 = h2.add_run("2. Singapore Top 50 AI / ML Startup Outreach Directory")
    r_h2.font.size = Pt(13)
    r_h2.font.bold = True
    r_h2.font.color.rgb = RGBColor(30, 58, 138)

    desc_p = doc.add_paragraph()
    desc_p.paragraph_format.space_before = Pt(0)
    desc_p.paragraph_format.space_after = Pt(6)
    r_desc = desc_p.add_run("Tip: All links in the ")
    r_desc.font.size = Pt(8.5)
    r_desc.font.color.rgb = RGBColor(71, 85, 105)
    r_desc_b = desc_p.add_run("Startup, Website, LinkedIn, and Founder Search")
    r_desc_b.font.size = Pt(8.5)
    r_desc_b.font.bold = True
    r_desc_b.font.color.rgb = RGBColor(30, 41, 59)
    r_desc_end = desc_p.add_run(" columns are directly clickable in Word and PDF viewers.")
    r_desc_end.font.size = Pt(8.5)
    r_desc_end.font.color.rgb = RGBColor(71, 85, 105)

    headers = [
        "Rank",
        "Startup Name",
        "AI / ML Specialization",
        "Size",
        "Signal",
        "Score",
        "Links",
        "Founder / CTO Search",
        "Target Role",
        "Outreach Status Log"
    ]

    col_widths = [
        Inches(0.45), # Rank
        Inches(1.35), # Startup
        Inches(1.85), # Area
        Inches(0.70), # Size
        Inches(0.95), # Signal
        Inches(0.60), # Score
        Inches(1.20), # Links (Web + LI)
        Inches(1.20), # Founder Search
        Inches(1.00), # Target Role
        Inches(0.70), # Status Log
    ]

    master_table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    master_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(master_table, color="D1D5DB", sz="4")

    # Header Row
    header_row = master_table.rows[0]
    make_row_header(header_row)
    prevent_row_split(header_row)

    for i, col_title in enumerate(headers):
        cell = header_row.cells[i]
        set_cell_background(cell, "1E293B")
        set_cell_margins(cell, top=90, bottom=90, left=60, right=60)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in [0, 3, 5] else WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(col_title)
        r.font.bold = True
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor(255, 255, 255)

    # Populate Rows
    for idx, (name, area, size, signal, score) in enumerate(rows, start=1):
        row = master_table.rows[idx]
        prevent_row_split(row)
        bg = "FFFFFF" if idx % 2 != 0 else "F8FAFC"

        # URLs
        li_url = company_links.get(name, "")
        if not li_url:
            li_url = f"https://www.linkedin.com/search/results/companies/?keywords={urllib.parse.quote(name)}%20Singapore"
        
        web_url = website.get(name, "")
        
        # Founder Search URL on LinkedIn
        founder_query = f"{name} Singapore founder OR CTO OR Head of AI"
        founder_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(founder_query)}"

        # 0: Rank
        c0 = row.cells[0]
        set_cell_background(c0, bg)
        set_cell_margins(c0, top=60, bottom=60, left=40, right=40)
        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r0 = p0.add_run(str(idx))
        r0.font.size = Pt(8)
        r0.font.bold = True
        r0.font.color.rgb = RGBColor(71, 85, 105)

        # 1: Startup Name (Clickable link to website if available)
        c1 = row.cells[1]
        set_cell_background(c1, bg)
        set_cell_margins(c1, top=60, bottom=60, left=60, right=60)
        p1 = c1.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        if web_url:
            add_hyperlink(p1, web_url, name, color="0F172A", underline=False, bold=True, font_size=8.5)
        else:
            r1 = p1.add_run(name)
            r1.font.bold = True
            r1.font.size = Pt(8.5)
            r1.font.color.rgb = RGBColor(15, 23, 42)

        # 2: AI / ML Specialization
        c2 = row.cells[2]
        set_cell_background(c2, bg)
        set_cell_margins(c2, top=60, bottom=60, left=60, right=60)
        p2 = c2.paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r2 = p2.add_run(area)
        r2.font.size = Pt(7.5)
        r2.font.color.rgb = RGBColor(51, 65, 85)

        # 3: Team Size
        c3 = row.cells[3]
        set_cell_background(c3, bg)
        set_cell_margins(c3, top=60, bottom=60, left=40, right=40)
        p3 = c3.paragraphs[0]
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r3 = p3.add_run(size)
        r3.font.size = Pt(7.5)
        r3.font.color.rgb = RGBColor(71, 85, 105)

        # 4: Hiring / Growth Signal
        c4 = row.cells[4]
        set_cell_background(c4, bg)
        set_cell_margins(c4, top=60, bottom=60, left=50, right=50)
        p4 = c4.paragraphs[0]
        p4.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r4 = p4.add_run(signal)
        r4.font.size = Pt(7.5)
        if "Active" in signal or "Hiring" in signal:
            r4.font.bold = True
            r4.font.color.rgb = RGBColor(22, 101, 52) # Forest Green
        elif "Growing" in signal:
            r4.font.bold = True
            r4.font.color.rgb = RGBColor(30, 64, 175) # Blue
        else:
            r4.font.color.rgb = RGBColor(100, 116, 139)

        # 5: Priority Score
        c5 = row.cells[5]
        set_cell_background(c5, bg)
        set_cell_margins(c5, top=60, bottom=60, left=40, right=40)
        p5 = c5.paragraphs[0]
        p5.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r5 = p5.add_run(score)
        r5.font.size = Pt(8)
        r5.font.bold = True
        if score == "10/10":
            r5.font.color.rgb = RGBColor(180, 83, 9) # Amber Gold / High tier
        elif score == "9.5/10":
            r5.font.color.rgb = RGBColor(37, 99, 235) # Bright Blue
        else:
            r5.font.color.rgb = RGBColor(71, 85, 105)

        # 6: Company Links (Website & LinkedIn)
        c6 = row.cells[6]
        set_cell_background(c6, bg)
        set_cell_margins(c6, top=60, bottom=60, left=50, right=50)
        p6 = c6.paragraphs[0]
        p6.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # Add Website link
        if web_url:
            add_hyperlink(p6, web_url, "🌐 Website", color="2563EB", underline=True, bold=False, font_size=7.5)
            p6.add_run("  ")
        else:
            rw = p6.add_run("🌐 —  ")
            rw.font.size = Pt(7.5)
            rw.font.color.rgb = RGBColor(148, 163, 184)
            
        # Add LinkedIn link
        add_hyperlink(p6, li_url, "💼 LinkedIn", color="0284C7", underline=True, bold=False, font_size=7.5)

        # 7: Founder / CTO Search (1-click search query)
        c7 = row.cells[7]
        set_cell_background(c7, bg)
        set_cell_margins(c7, top=60, bottom=60, left=50, right=50)
        p7 = c7.paragraphs[0]
        p7.alignment = WD_ALIGN_PARAGRAPH.LEFT
        add_hyperlink(p7, founder_url, "🔍 Find Founder/CTO", color="7C3AED", underline=True, bold=True, font_size=7.5)

        # 8: Target Role
        c8 = row.cells[8]
        set_cell_background(c8, bg)
        set_cell_margins(c8, top=60, bottom=60, left=50, right=50)
        p8 = c8.paragraphs[0]
        p8.alignment = WD_ALIGN_PARAGRAPH.LEFT
        role_label = "AI/ML Intern"
        if "Robotics" in area:
            role_label = "Robotics/AI Intern"
        elif "GenAI" in area or "LLM" in area:
            role_label = "GenAI/ML Intern"
        elif "Computer vision" in area:
            role_label = "CV/ML Intern"
        elif "Voice" in area:
            role_label = "Voice AI/NLP Intern"
        r8 = p8.add_run(role_label)
        r8.font.size = Pt(7.5)
        r8.font.color.rgb = RGBColor(51, 65, 85)

        # 9: Status / Outreach Tracker Checkbox
        c9 = row.cells[9]
        set_cell_background(c9, bg)
        set_cell_margins(c9, top=60, bottom=60, left=40, right=40)
        p9 = c9.paragraphs[0]
        p9.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r9 = p9.add_run("☐ Not contacted\n☐ Connected\n☐ Replied")
        r9.font.size = Pt(6.5)
        r9.font.color.rgb = RGBColor(100, 116, 139)

    # Set column widths across all rows
    for row in master_table.rows:
        for i, w in enumerate(col_widths):
            row.cells[i].width = w

    doc.add_page_break()

    # ---------------------------------------------------------
    # 4. Section 3: Priority Tier Dossier & Outreach Playbook
    # ---------------------------------------------------------
    h3 = doc.add_paragraph()
    h3.paragraph_format.space_before = Pt(0)
    h3.paragraph_format.space_after = Pt(4)
    r_h3 = h3.add_run("3. High-Priority Target Profiles (10/10 Tier 1 Startups)")
    r_h3.font.size = Pt(13)
    r_h3.font.bold = True
    r_h3.font.color.rgb = RGBColor(30, 58, 138)

    desc_tier = doc.add_paragraph()
    desc_tier.paragraph_format.space_before = Pt(0)
    desc_tier.paragraph_format.space_after = Pt(8)
    r_tier = desc_tier.add_run("These 8 companies represent the highest priority outreach targets based on recent funding, active team expansion, and cutting-edge GenAI/Agentic systems. Click any link below to visit their domain or launch pre-configured LinkedIn search.")
    r_tier.font.size = Pt(8.5)
    r_tier.font.color.rgb = RGBColor(71, 85, 105)

    tier1_companies = [r for r in rows if r[4] == "10/10"]
    
    # 2-column dossier cards table
    dossier_table = doc.add_table(rows=(len(tier1_companies) + 1) // 2, cols=2)
    dossier_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(dossier_table, color="CBD5E1", sz="6")

    card_widths = [Inches(4.95), Inches(4.95)]

    for idx, (name, area, size, signal, score) in enumerate(tier1_companies):
        r_idx = idx // 2
        c_idx = idx % 2
        cell = dossier_table.cell(r_idx, c_idx)
        set_cell_background(cell, "F8FAFC")
        set_cell_margins(cell, top=100, bottom=100, left=140, right=140)

        web_url = website.get(name, "")
        li_url = company_links.get(name, f"https://www.linkedin.com/search/results/companies/?keywords={urllib.parse.quote(name)}")
        f_query = f"{name} Singapore founder OR CTO"
        f_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(f_query)}"

        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2)

        # Company Title & Priority Badge
        r_name = p.add_run(f"#{idx+1} {name}  ")
        r_name.font.size = Pt(10.5)
        r_name.font.bold = True
        r_name.font.color.rgb = RGBColor(15, 23, 42)

        r_badge = p.add_run(f"[{score} • {signal}]")
        r_badge.font.size = Pt(8.5)
        r_badge.font.bold = True
        r_badge.font.color.rgb = RGBColor(180, 83, 9)

        # Area & Team size
        p_sub = cell.add_paragraph()
        p_sub.paragraph_format.space_before = Pt(0)
        p_sub.paragraph_format.space_after = Pt(3)
        r_dom = p_sub.add_run(f"Focus: {area} | Headcount: {size}")
        r_dom.font.size = Pt(8)
        r_dom.font.italic = True
        r_dom.font.color.rgb = RGBColor(71, 85, 105)

        # Hyperlinks block
        p_links = cell.add_paragraph()
        p_links.paragraph_format.space_before = Pt(0)
        p_links.paragraph_format.space_after = Pt(3)
        
        if web_url:
            add_hyperlink(p_links, web_url, "🌐 Official Website", color="2563EB", underline=True, bold=True, font_size=8)
            p_links.add_run("   |   ")
        add_hyperlink(p_links, li_url, "💼 Company LinkedIn", color="0284C7", underline=True, bold=True, font_size=8)
        p_links.add_run("   |   ")
        add_hyperlink(p_links, f_url, "🔍 Find Founder/CTO", color="7C3AED", underline=True, bold=True, font_size=8)

        # Recommended Pitch Angle
        p_pitch = cell.add_paragraph()
        p_pitch.paragraph_format.space_before = Pt(0)
        p_pitch.paragraph_format.space_after = Pt(0)
        r_pitch_lbl = p_pitch.add_run("Recommended Outreach Angle: ")
        r_pitch_lbl.font.size = Pt(8)
        r_pitch_lbl.font.bold = True
        r_pitch_lbl.font.color.rgb = RGBColor(30, 41, 59)

        angle = "Agentic workflows, model evaluation, and autonomous execution pipelines."
        if "video" in area.lower():
            angle = "Diffusion models, spatio-temporal video generation, and inference optimization."
        elif "robotics" in area.lower():
            angle = "Embodied AI, visual-spatial reasoning, and simulation-to-real robotic policy transfer."
        elif "chips" in area.lower() or "compute" in area.lower():
            angle = "Edge ML acceleration, quantization, TensorRT/ONNX deployment, and low-latency inference."
        elif "aws" in area.lower():
            angle = "Cloud-native GenAI pipelines, Bedrock/SageMaker deployment, and enterprise LLM integration."

        r_pitch = p_pitch.add_run(angle)
        r_pitch.font.size = Pt(8)
        r_pitch.font.color.rgb = RGBColor(71, 85, 105)

    # Set dossier widths
    for row in dossier_table.rows:
        for i, w in enumerate(card_widths):
            row.cells[i].width = w

    # ---------------------------------------------------------
    # 5. Section 4: Tailored Cold Outreach Message Templates
    # ---------------------------------------------------------
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    h4 = doc.add_paragraph()
    h4.paragraph_format.space_before = Pt(8)
    h4.paragraph_format.space_after = Pt(4)
    r_h4 = h4.add_run("4. High-Conversion Outreach Message Templates")
    r_h4.font.size = Pt(13)
    r_h4.font.bold = True
    r_h4.font.color.rgb = RGBColor(30, 58, 138)

    templates_table = doc.add_table(rows=3, cols=2)
    templates_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(templates_table, color="CBD5E1", sz="4")

    tpl_col_widths = [Inches(2.5), Inches(7.4)]

    templates_data = [
        (
            "Template 1: LinkedIn Connection Request Note\n(<300 characters limit)",
            "Hi [Founder Name], came across [Company Name]'s impressive work in [Area, e.g. Agentic AI / Embodied Robotics]. I'm an AI/ML student focusing on [Tech, e.g. LangGraph/PyTorch/Diffusion]. Would love to connect and follow your journey in Singapore's AI ecosystem!"
        ),
        (
            "Template 2: Follow-Up Value Pitch Message\n(Send within 24h after connecting)",
            "Hi [Name], thanks for connecting! I've been tracking [Company Name]'s recent progress in [e.g. multi-agent reasoning / autonomous vision]. I'm seeking an AI/ML Intern / GenAI Intern role where I can actively contribute.\n\nMy core stack includes Python, PyTorch, [HuggingFace / vLLM / OpenCV / ROS], and I recently built [Brief 1-sentence mention of relevant GitHub project with metric].\n\nI’d love 10 minutes to learn about your current engineering priorities and share how I could contribute to your team this coming term. Open to sending my CV or repo?"
        ),
        (
            "Template 3: Polite Follow-Up Nudge\n(Send 5 days after Message 1 if no reply)",
            "Hi [Name], hope you're having a productive week! Just following up on my note regarding AI/ML internship opportunities at [Company Name]. I know you're super busy scaling the team—happy to share a quick 1-pager on how my technical background aligns with your current roadmap whenever convenient."
        )
    ]

    for t_idx, (title, content) in enumerate(templates_data):
        row = templates_table.rows[t_idx]
        prevent_row_split(row)
        bg = "FFFFFF" if t_idx % 2 == 0 else "F8FAFC"
        
        c_title = row.cells[0]
        set_cell_background(c_title, "F1F5F9")
        set_cell_margins(c_title, top=80, bottom=80, left=100, right=100)
        p_t = c_title.paragraphs[0]
        r_t = p_t.add_run(title)
        r_t.font.bold = True
        r_t.font.size = Pt(8.5)
        r_t.font.color.rgb = RGBColor(30, 58, 138)

        c_cnt = row.cells[1]
        set_cell_background(c_cnt, bg)
        set_cell_margins(c_cnt, top=80, bottom=80, left=120, right=120)
        p_c = c_cnt.paragraphs[0]
        r_c = p_c.add_run(content)
        r_c.font.size = Pt(8.5)
        r_c.font.color.rgb = RGBColor(30, 41, 59)

    for row in templates_table.rows:
        for i, w in enumerate(tpl_col_widths):
            row.cells[i].width = w

    # Save document
    doc.save(output_path)
    print(f"Document successfully created at: {output_path}")

if __name__ == "__main__":
    out_file = r"f:\esp32testbluetoo\Singapore_AI_ML_Startup_Outreach_50.docx"
    build_outreach_document(out_file)
