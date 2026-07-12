import os
import re
import uuid
import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "hackathon_policy_secret_key"

# In-memory storage for session analysis results (clean database-less architecture)
SESSION_DATA = {}

# System constant date (July 12, 2026)
CURRENT_DATE = datetime.date(2026, 7, 12)

# Keywords and Regex patterns
DEPRECATED_TERMS = [
    "TLS 1.0", "TLS 1.1", "SHA-1", "MD5", "Windows Server 2012", 
    "Windows Server 2008", "Windows 7", "Windows XP", "SSL 3.0", 
    "DES", "3DES", "RC4"
]

CATEGORY_PATTERNS = {
    'Password': re.compile(r'\b(password|passcode|credential|pin)\b', re.IGNORECASE),
    'Encryption': re.compile(r'\b(encrypt|cipher|tls|ssl|cryptographic|aes|rsa|ssh)\b', re.IGNORECASE),
    'Access Control': re.compile(r'\b(access|authorize|role|permission|privilege|rbac|abac|login|account)\b', re.IGNORECASE),
    'Data Retention': re.compile(r'\b(retain|retention|archive|purge|delete after|keep for|dispose)\b', re.IGNORECASE),
    'Logging': re.compile(r'\b(log|audit|event|monitor|siem|syslog)\b', re.IGNORECASE),
    'Network': re.compile(r'\b(network|firewall|port|ip address|subnet|vpn|dns|router|switch)\b', re.IGNORECASE),
    'Backup': re.compile(r'\b(backup|disaster recovery|dr|restore|replication|failover)\b', re.IGNORECASE),
    'MFA': re.compile(r'\b(mfa|2fa|multi-factor|two-factor|otp|authenticator)\b', re.IGNORECASE),
}

def get_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

def parse_policy_date(text):
    # Search YYYY-MM-DD or YYYY/MM/DD
    m1 = re.search(r'\b(\d{4})[-/](\d{2})[-/](\d{2})\b', text)
    if m1:
        try:
            return datetime.date(int(m1.group(1)), int(m1.group(2)), int(m1.group(3)))
        except ValueError:
            pass
    # Search MM-DD-YYYY or MM/DD/YYYY
    m2 = re.search(r'\b(\d{2})[-/](\d{2})[-/](\d{4})\b', text)
    if m2:
        try:
            return datetime.date(int(m2.group(3)), int(m2.group(1)), int(m2.group(2)))
        except ValueError:
            pass
    return None

def extract_sentences(text):
    lines = text.split('\n')
    sentences = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip lines that look like metadata
        if any(line.lower().startswith(m) for m in ['last reviewed:', 'review date:', 'date:', 'status:', 'created:']):
            continue
        # Strip headers and list symbols
        line = re.sub(r'^#+\s*', '', line)
        line = re.sub(r'^(\d+\.)+\d*\s*', '', line)
        line = re.sub(r'^[-*+•]\s*', '', line)
        line = line.strip()
        if not line:
            continue
        # Split into sentences based on punctuation followed by space or end of string
        parts = re.split(r'(?<=[.!?])\s+', line)
        for p in parts:
            p = p.strip()
            if p:
                sentences.append(p)
    return sentences

def check_obligation(sentence):
    s = sentence.lower()
    # Check negative obligation first
    if re.search(r'\b(must not|prohibited|shall not|should not)\b', s):
        return True, False
    # Check positive obligation
    elif re.search(r'\b(must|shall|should|required)\b', s):
        return True, True
    return False, None

def classify_category(sentence):
    for cat, pattern in CATEGORY_PATTERNS.items():
        if pattern.search(sentence):
            return cat
    return 'Others'

def clean_tokens(sentence):
    s = re.sub(r'[^\w\s]', '', sentence.lower())
    tokens = s.split()
    stop_words = {
        'a', 'an', 'the', 'is', 'are', 'was', 'were', 'to', 'for', 'in', 'on', 'at', 'by', 
        'with', 'from', 'of', 'and', 'or', 'but', 'if', 'this', 'that', 'these', 'those', 
        'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'must', 'shall', 
        'should', 'required', 'prohibited', 'not', 'no', 'any', 'all', 'policy', 'policies',
        'guidelines', 'requirements', 'standard', 'standards', 'within', 'under', 'for'
    }
    return {w for w in tokens if w not in stop_words and len(w) > 2}

def run_analysis(policies):
    # policies: dict of {filename: file_content}
    all_obligations = []
    policy_metadata = {}
    
    for filename, content in policies.items():
        # 1. Parse date and calculate staleness
        reviewed_date = parse_policy_date(content)
        is_stale = False
        age_months = None
        if reviewed_date:
            months = (CURRENT_DATE.year - reviewed_date.year) * 12 + (CURRENT_DATE.month - reviewed_date.month)
            is_stale = months > 18
            age_months = months
        
        # 2. Check for deprecated terms
        detected_deprecated = []
        for term in DEPRECATED_TERMS:
            if re.search(r'\b' + re.escape(term) + r'\b', content, re.IGNORECASE):
                detected_deprecated.append(term)
                
        policy_metadata[filename] = {
            'reviewed_date': reviewed_date.strftime('%Y-%m-%d') if reviewed_date else 'Not Found',
            'is_stale_by_date': is_stale,
            'age_months': age_months,
            'deprecated_terms': detected_deprecated,
            'is_stale_overall': is_stale or len(detected_deprecated) > 0
        }
        
        # 3. Extract obligations
        sentences = extract_sentences(content)
        for s in sentences:
            is_ob, is_pos = check_obligation(s)
            if is_ob:
                category = classify_category(s)
                all_obligations.append({
                    'sentence': s,
                    'file': filename,
                    'category': category,
                    'is_positive': is_pos
                })

    # 4. Detect Direct Conflicts (positive vs negative within category)
    direct_conflicts = []
    categories_grouped = {}
    for ob in all_obligations:
        cat = ob['category']
        if cat not in categories_grouped:
            categories_grouped[cat] = []
        categories_grouped[cat].append(ob)
        
    for cat, items in categories_grouped.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                s1 = items[i]
                s2 = items[j]
                if s1['is_positive'] != s2['is_positive']:
                    tokens1 = clean_tokens(s1['sentence'])
                    tokens2 = clean_tokens(s2['sentence'])
                    if tokens1 and tokens2:
                        common = tokens1 & tokens2
                        # Check Jaccard overlap of content words
                        similarity = len(common) / min(len(tokens1), len(tokens2))
                        if similarity >= 0.5:
                            direct_conflicts.append({
                                'category': cat,
                                'sentence1': s1['sentence'],
                                'file1': s1['file'],
                                'sentence2': s2['sentence'],
                                'file2': s2['file'],
                                'overlap_terms': list(common),
                                'details': f"Direct Conflict: One statement authorizes/requires what the other prohibits regarding the common term(s): {', '.join(common)}"
                            })

    # 5. Detect Retention Period Differences
    retention_conflicts = []
    retention_items = []
    retention_sentences = [ob for ob in all_obligations if ob['category'] == 'Data Retention']
    
    for item in retention_sentences:
        s = item['sentence'].lower()
        match = re.search(r'\b(\d+)\s*(year|month|day|week)s?\b', s)
        if match:
            val = int(match.group(1))
            unit = match.group(2)
            days = val
            if 'week' in unit:
                days = val * 7
            elif 'month' in unit:
                days = val * 30
            elif 'year' in unit:
                days = val * 365
                
            # Find subject context
            subjects = []
            for keyword in ['backup', 'log', 'audit', 'email', 'user data', 'access log', 'record', 'retention']:
                if keyword in s:
                    subjects.append(keyword)
            if not subjects:
                subjects = ['general data']
                
            retention_items.append({
                'sentence': item['sentence'],
                'file': item['file'],
                'subjects': subjects,
                'value_str': f"{val} {unit}(s)",
                'days': days
            })
            
    for i in range(len(retention_items)):
        for j in range(i + 1, len(retention_items)):
            r1 = retention_items[i]
            r2 = retention_items[j]
            common_subs = set(r1['subjects']) & set(r2['subjects'])
            # Exclude generic 'retention' or 'general data' if there's a more specific match
            if 'retention' in common_subs and len(common_subs) > 1:
                common_subs.remove('retention')
            if common_subs and r1['days'] != r2['days']:
                retention_conflicts.append({
                    'subject': ', '.join(common_subs),
                    'sentence1': r1['sentence'],
                    'file1': r1['file'],
                    'value1': r1['value_str'],
                    'sentence2': r2['sentence'],
                    'file2': r2['file'],
                    'value2': r2['value_str'],
                    'details': f"Retention Mismatch: Different retention durations set for '{list(common_subs)[0]}'."
                })

    # 6. Detect Redundant/Duplicate Policies
    redundancies = []
    for cat, items in categories_grouped.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                s1 = items[i]
                s2 = items[j]
                norm1 = re.sub(r'[^\w\s]', '', s1['sentence'].lower()).strip()
                norm2 = re.sub(r'[^\w\s]', '', s2['sentence'].lower()).strip()
                
                if norm1 == norm2:
                    # Don't duplicate redundancy alerts
                    redundancies.append({
                        'category': cat,
                        'sentence1': s1['sentence'],
                        'file1': s1['file'],
                        'sentence2': s2['sentence'],
                        'file2': s2['file'],
                        'type': 'Duplicate',
                        'details': 'Identical statements found.'
                    })
                else:
                    w1 = set(norm1.split())
                    w2 = set(norm2.split())
                    if w1 and w2:
                        jaccard = len(w1 & w2) / len(w1 | w2)
                        if jaccard >= 0.85:
                            redundancies.append({
                                'category': cat,
                                'sentence1': s1['sentence'],
                                'file1': s1['file'],
                                'sentence2': s2['sentence'],
                                'file2': s2['file'],
                                'type': 'Redundant',
                                'details': f"Redundant: Very high similarity ({int(jaccard*100)}% word overlap)."
                            })

    # Calculate policy health score
    score = 100
    # Deductions
    score -= len(direct_conflicts) * 15
    score -= len(retention_conflicts) * 10
    score -= len(redundancies) * 5
    
    stale_files_count = 0
    deprecated_terms_count = 0
    for meta in policy_metadata.values():
        if meta['is_stale_by_date']:
            stale_files_count += 1
            score -= 10
        if meta['deprecated_terms']:
            deprecated_terms_count += len(meta['deprecated_terms'])
            score -= len(meta['deprecated_terms']) * 5
            
    score = max(0, score)
    
    # Calculate health rating
    if score >= 90:
        rating = 'Excellent'
        badge_class = 'bg-success'
    elif score >= 75:
        rating = 'Good'
        badge_class = 'bg-info text-dark'
    elif score >= 50:
        rating = 'Fair'
        badge_class = 'bg-warning text-dark'
    else:
        rating = 'Poor'
        badge_class = 'bg-danger'

    # Prepare category count for Pie Chart
    cat_counts = {cat: 0 for cat in CATEGORY_PATTERNS.keys()}
    cat_counts['Others'] = 0
    for ob in all_obligations:
        cat_counts[ob['category']] += 1

    return {
        'total_policies': len(policies),
        'obligations': all_obligations,
        'metadata': policy_metadata,
        'direct_conflicts': direct_conflicts,
        'retention_conflicts': retention_conflicts,
        'redundancies': redundancies,
        'health_score': score,
        'health_rating': rating,
        'badge_class': badge_class,
        'category_distribution': cat_counts,
        'stale_count': stale_files_count,
        'deprecated_count': deprecated_terms_count
    }

@app.route('/')
def index():
    session_id = get_session_id()
    results = SESSION_DATA.get(session_id, None)
    return render_template('index.html', results=results, current_date=CURRENT_DATE.strftime('%Y-%m-%d'))

@app.route('/upload', methods=['POST'])
def upload_files():
    session_id = get_session_id()
    uploaded_files = request.files.getlist('policies')
    
    if not uploaded_files or uploaded_files[0].filename == '':
        return jsonify({'error': 'No files uploaded'}), 400
        
    policies = {}
    for f in uploaded_files:
        if f.filename.endswith(('.txt', '.md')):
            try:
                content = f.read().decode('utf-8', errors='ignore')
                policies[f.filename] = content
            except Exception as e:
                return jsonify({'error': f"Failed to read file {f.filename}: {str(e)}"}), 500
                
    if not policies:
        return jsonify({'error': 'Only .txt and .md files are supported.'}), 400
        
    results = run_analysis(policies)
    SESSION_DATA[session_id] = results
    return jsonify({'success': True})

@app.route('/load-samples', methods=['POST'])
def load_samples():
    session_id = get_session_id()
    sample_dir = os.path.join(app.root_path, 'sample_policies')
    if not os.path.exists(sample_dir):
        return jsonify({'error': 'Sample policies directory not found.'}), 404
        
    policies = {}
    for filename in os.listdir(sample_dir):
        if filename.endswith(('.txt', '.md')):
            filepath = os.path.join(sample_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    policies[filename] = f.read()
            except Exception as e:
                return jsonify({'error': f"Failed to read sample {filename}: {str(e)}"}), 500
                
    if not policies:
        return jsonify({'error': 'No sample files found in sample_policies/'}), 404
        
    results = run_analysis(policies)
    SESSION_DATA[session_id] = results
    return jsonify({'success': True})

@app.route('/clear', methods=['POST'])
def clear_data():
    session_id = get_session_id()
    if session_id in SESSION_DATA:
        del SESSION_DATA[session_id]
    return redirect(url_for('index'))

@app.route('/download-pdf')
def download_pdf():
    session_id = get_session_id()
    results = SESSION_DATA.get(session_id, None)
    if not results:
        return redirect(url_for('index'))
        
    # Temporary PDF file
    temp_dir = os.path.join(app.root_path, 'scratch')
    os.makedirs(temp_dir, exist_ok=True)
    pdf_filename = f"policy_report_{session_id[:8]}.pdf"
    pdf_path = os.path.join(temp_dir, pdf_filename)
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom Palette
    color_primary = colors.HexColor('#161821')
    color_accent = colors.HexColor('#00f0ff')
    color_text = colors.HexColor('#2e3440')
    
    # Custom Paragraph Styles
    style_title = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=color_primary,
        spaceAfter=15
    )
    
    style_subtitle = ParagraphStyle(
        name='SubTitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        textColor=colors.HexColor('#5e6c84'),
        spaceAfter=30
    )
    
    style_section = ParagraphStyle(
        name='SectionStyle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=color_primary,
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    style_cell = ParagraphStyle(
        name='CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=color_text
    )
    
    style_cell_bold = ParagraphStyle(
        name='CellTextBold',
        parent=style_cell,
        fontName='Helvetica-Bold'
    )
    
    style_cell_header = ParagraphStyle(
        name='CellHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white
    )
    
    story = []
    
    # Cover / Header
    story.append(Paragraph("Policy Conflict & Staleness Analysis Report", style_title))
    story.append(Paragraph(f"Generated on {datetime.date.today().strftime('%B %d, %Y')} | Assessment Date: {CURRENT_DATE.strftime('%B %d, %Y')}", style_subtitle))
    story.append(Spacer(1, 10))
    
    # Health Overview Table
    overall_data = [
        [Paragraph("Assessment Attribute", style_cell_header), Paragraph("Result / Value", style_cell_header)],
        [Paragraph("Total Policies Checked", style_cell), Paragraph(str(results['total_policies']), style_cell_bold)],
        [Paragraph("Overall Policy Health Score", style_cell), Paragraph(f"{results['health_score']}/100 ({results['health_rating']})", style_cell_bold)],
        [Paragraph("Direct Modal Conflicts", style_cell), Paragraph(str(len(results['direct_conflicts'])), style_cell_bold)],
        [Paragraph("Data Retention Mismatches", style_cell), Paragraph(str(len(results['retention_conflicts'])), style_cell_bold)],
        [Paragraph("Redundant Policy Statements", style_cell), Paragraph(str(len(results['redundancies'])), style_cell_bold)],
        [Paragraph("Stale Policies (Reviewed > 18 Months Ago)", style_cell), Paragraph(str(results['stale_count']), style_cell_bold)],
        [Paragraph("Deprecated Tech Terms Found", style_cell), Paragraph(str(results['deprecated_count']), style_cell_bold)]
    ]
    
    t_summary = Table(overall_data, colWidths=[250, 250])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), color_primary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e1e4e8')),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8f9fa')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ('TOPPADDING', (0,1), (-1,-1), 6),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 20))
    
    # Direct & Retention Conflicts Section
    story.append(Paragraph("1. Direct Policy & Retention Conflicts", style_section))
    all_conflicts = results['direct_conflicts'] + results['retention_conflicts']
    
    if not all_conflicts:
        story.append(Paragraph("No active conflicts or retention mismatches detected between policies.", style_cell))
    else:
        conflict_table_data = [
            [
                Paragraph("Type / Subject", style_cell_header), 
                Paragraph("Directive 1 (Source File)", style_cell_header), 
                Paragraph("Directive 2 (Source File)", style_cell_header)
            ]
        ]
        
        for dc in results['direct_conflicts']:
            conflict_table_data.append([
                Paragraph(f"Direct Modal Conflict<br/>({dc['category']})", style_cell_bold),
                Paragraph(f"\"{dc['sentence1']}\"<br/><font color='#777'>Source: {dc['file1']}</font>", style_cell),
                Paragraph(f"\"{dc['sentence2']}\"<br/><font color='#777'>Source: {dc['file2']}</font>", style_cell)
            ])
            
        for rc in results['retention_conflicts']:
            conflict_table_data.append([
                Paragraph(f"Retention Mismatch<br/>({rc['subject']})", style_cell_bold),
                Paragraph(f"\"{rc['sentence1']}\"<br/><font color='#777'>Source: {rc['file1']} ({rc['value1']})</font>", style_cell),
                Paragraph(f"\"{rc['sentence2']}\"<br/><font color='#777'>Source: {rc['file2']} ({rc['value2']})</font>", style_cell)
            ])
            
        t_conflicts = Table(conflict_table_data, colWidths=[100, 200, 200])
        t_conflicts.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#821818')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e1e4e8')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#fcf8f8')]),
        ]))
        story.append(t_conflicts)
        
    story.append(Spacer(1, 20))
    
    # Stale & Deprecated Terms Section
    story.append(Paragraph("2. Policy Review Staleness & Deprecations", style_section))
    stale_table_data = [
        [
            Paragraph("Policy Filename", style_cell_header), 
            Paragraph("Last Reviewed", style_cell_header), 
            Paragraph("Age (Months)", style_cell_header), 
            Paragraph("Deprecated Terms Detected", style_cell_header)
        ]
    ]
    
    for filename, meta in results['metadata'].items():
        age_str = f"{meta['age_months']} m" if meta['age_months'] is not None else 'N/A'
        dep_terms_str = ', '.join(meta['deprecated_terms']) if meta['deprecated_terms'] else 'None'
        
        # Color highlight for status
        if meta['is_stale_overall']:
            bg_color = colors.HexColor('#fff9e6')
            status_text = f"<font color='red'><b>{filename}</b></font>"
        else:
            bg_color = colors.white
            status_text = filename
            
        stale_table_data.append([
            Paragraph(status_text, style_cell),
            Paragraph(meta['reviewed_date'], style_cell),
            Paragraph(age_str, style_cell),
            Paragraph(dep_terms_str, style_cell_bold if meta['deprecated_terms'] else style_cell)
        ])
        
    t_stale = Table(stale_table_data, colWidths=[180, 100, 80, 140])
    t_stale.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#8a6d1c')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e1e4e8')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    # Apply row backgrounds dynamically
    for idx, (filename, meta) in enumerate(results['metadata'].items(), start=1):
        if meta['is_stale_overall']:
            t_stale.setStyle(TableStyle([('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#fff9e6'))]))
            
    story.append(t_stale)
    story.append(Spacer(1, 20))
    
    # Redundant Policies Section
    story.append(Paragraph("3. Redundant / Duplicate Policy Statements", style_section))
    if not results['redundancies']:
        story.append(Paragraph("No duplicate or redundant policy statements detected.", style_cell))
    else:
        redundant_table_data = [
            [
                Paragraph("Type / Category", style_cell_header), 
                Paragraph("Statement 1 (File)", style_cell_header), 
                Paragraph("Statement 2 (File)", style_cell_header)
            ]
        ]
        
        for red in results['redundancies']:
            redundant_table_data.append([
                Paragraph(f"{red['type']}<br/>({red['category']})", style_cell_bold),
                Paragraph(f"\"{red['sentence1']}\"<br/><font color='#777'>Source: {red['file1']}</font>", style_cell),
                Paragraph(f"\"{red['sentence2']}\"<br/><font color='#777'>Source: {red['file2']}</font>", style_cell)
            ])
            
        t_redundant = Table(redundant_table_data, colWidths=[100, 200, 200])
        t_redundant.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4a5568')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e1e4e8')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f7fafc')]),
        ]))
        story.append(t_redundant)
        
    doc.build(story)
    return send_file(pdf_path, as_attachment=True, download_name=f"Policy_Detector_Report.pdf")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
