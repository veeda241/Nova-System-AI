#!/usr/bin/env python3
"""
# NOVA Professional Documentation Suite v12.0
# MASTER TABLE OF CONTENTS & CONTENT ALIGNMENT
# ---------------------------------------------
# Features:
# 1. Full Table of Contents (TOC) on Page 2
# 2. PART Divider Logic (Starts on new pages)
# 3. Dynamic Header/Footer tracking
# 4. Content starting immediately after TOC
"""

import os
import sys
import re
from datetime import datetime

try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
except ImportError:
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'fpdf2', '-q'])
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

class NovaPDF(FPDF):
    def __init__(self, title_text):
        super().__init__()
        self.doc_title = title_text
        self.current_section_title = "TECHNICAL MANUAL"
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', 'B', 9)
            self.set_text_color(180, 180, 180)
            self.set_xy(10, 8)
            self.cell(0, 10, f"NOVA SYSTEM AI | v2.0 EVOLUTION", align='L')
            self.set_xy(10, 8)
            self.cell(0, 10, f"{self.current_section_title} | Page {self.page_no()}", align='R')
            self.ln(10)
            self.set_draw_color(220, 220, 220)
            self.line(10, 18, 200, 18)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(180, 180, 180)
        self.cell(0, 10, "CONFIDENTIAL - AUTHORIZED ACCESS ONLY - © 2026 Nova Research Labs", align='C')

    def clean_text(self, text):
        text = text.replace('∈', ' in ').replace('ℝ', 'R').replace('×', ' x ')
        text = text.replace('∂', 'd').replace('Σ', 'Sum').replace('√', 'sqrt')
        text = text.replace('δ', 'delta').replace('^T', '.T')
        text = text.replace('↓', 'v').replace('┌', '+').replace('┐', '+')
        text = text.replace('└', '+').replace('┘', '+').replace('│', '|')
        text = text.replace('─', '-').replace('├──', '|--').replace('└──', '`--')
        text = text.replace('**', '').replace('*', '')
        return text.encode('ascii', errors='ignore').decode('ascii')

    def draw_bullet(self, text):
        text = self.clean_text(text)
        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(40, 40, 40)
        start_y = self.get_y()
        self.set_x(15)
        self.cell(5, 5, chr(149), border=0) 
        orig_margin = self.l_margin
        self.set_left_margin(20)
        self.set_y(start_y)
        self.multi_cell(0, 5, text, border=0, align='L')
        self.set_left_margin(orig_margin)
        self.ln(0.5)

    def draw_code_box(self, code_lines):
        if not code_lines: return
        self.ln(2)
        self.set_font("Courier", "", 9)
        self.set_text_color(0, 50, 0)
        h = len(code_lines) * 4.5 + 4
        if self.get_y() + h > 270: self.add_page()
        curr_y = self.get_y()
        self.set_fill_color(248, 248, 248)
        self.rect(10, curr_y, 190, h, "F")
        self.set_draw_color(200, 200, 200)
        self.rect(10, curr_y, 190, h, "D")
        self.set_xy(12, curr_y + 2)
        for line in code_lines:
            self.cell(0, 4.5, self.clean_text(line), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def draw_markdown_table(self, table_lines):
        if not table_lines: return
        rows = []
        for line in table_lines:
            if '---' in line and '|' in line: continue
            s = line.strip()
            if s.startswith('|'): s = s[1:]
            if s.endswith('|'): s = s[:-1]
            cells = [self.clean_text(c.strip()) for c in s.split('|')]
            if any(cells): rows.append(cells)
        if not rows: return
        num_cols = max(len(r) for r in rows)
        col_chars = [0] * num_cols
        for row in rows:
            for i, cell in enumerate(row):
                if i < num_cols: col_chars[i] = max(col_chars[i], len(cell))
        total = sum(col_chars)
        if total == 0: return
        widths = [(max(w, 5) / total) * 190 for w in col_chars]
        for i, row in enumerate(rows):
            is_header = (i == 0)
            if is_header:
                self.set_font("Helvetica", "B", 9); self.set_fill_color(0, 40, 80); self.set_text_color(255, 255, 255)
            else:
                self.set_font("Helvetica", "", 9); self.set_fill_color(245, 245, 250) if i % 2 == 0 else self.set_fill_color(255, 255, 255)
                self.set_text_color(40, 40, 40)
            
            # Row height calc
            line_counts = []
            for j, cell in enumerate(row):
                if j < widths.__len__():
                    tw = self.get_string_width(cell)
                    lines_needed = int(tw / (widths[j]-2)) + 1
                    line_counts.append(lines_needed)
            rh = max(line_counts) * 5 if line_counts else 6
            
            if self.get_y() + rh > 270: self.add_page()
            cy = self.get_y(); self.set_x(10)
            for j, cell in enumerate(row):
                if j < num_cols:
                    self.multi_cell(widths[j], 5, cell, border=1, align='C', fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_y(cy + rh)
        self.ln(4); self.set_text_color(0, 0, 0)

def generate_manual():
    md_path = os.path.join(os.path.dirname(__file__), "NOVA_System_AI_Complete_Documentation.md")
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    pdf = NovaPDF("NOVA MASTER MANUAL")
    
    # --- 1. COVER PAGE ---
    pdf.add_page()
    pdf.set_fill_color(0, 40, 80)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.set_font("Helvetica", "B", 48)
    pdf.set_text_color(255, 255, 255); pdf.set_y(100)
    pdf.multi_cell(0, 20, "NOVA\nMASTER TECHNICAL\nMANUAL", align="C")
    pdf.ln(10); pdf.set_font("Helvetica", "", 18)
    pdf.multi_cell(0, 10, "v2.0 Evolution Release\nArchitecture | Intelligence | Automation", align="C")
    
    # --- 2. TABLE OF CONTENTS (SCAN) ---
    lines = content.split("\n")
    toc_entries = []
    for line in lines:
        if line.startswith("# "): toc_entries.append((1, line[2:].strip()))
        elif line.startswith("## "): toc_entries.append((2, line[3:].strip()))

    # --- 3. RENDER TOC ON PAGE 2 ---
    pdf.add_page()
    pdf.current_section_title = "TABLE OF CONTENTS"
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(0, 40, 80)
    pdf.cell(0, 15, "Table of Contents", border="B", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 11)
    for level, title in toc_entries:
        pdf.set_text_color(0, 40, 80) if level == 1 else pdf.set_text_color(60, 60, 60)
        self_x = 15 if level == 1 else 25
        pdf.set_x(self_x)
        pdf.set_font("Helvetica", "B" if level == 1 else "", 11 if level == 1 else 10)
        pdf.cell(0, 8, title, ln=True)
    
    # --- 4. CONTENT GENERATION START ---
    table_buffer = []
    code_buffer = []
    in_table = False
    in_code = False
    
    for line in lines:
        stripped = line.strip()
        
        # Code Blocks
        if stripped.startswith("```"):
            if in_code:
                pdf.draw_code_box(code_buffer)
                code_buffer = []
                in_code = False
            else:
                in_code = True
            continue
        elif in_code:
            code_buffer.append(line); continue

        # Tables
        if stripped.startswith("|") and "|" in stripped:
            in_table = True; table_buffer.append(line); continue
        elif in_table:
            pdf.draw_markdown_table(table_buffer); table_buffer = []; in_table = False

        # Formatting
        if stripped.startswith("# "):
            pdf.add_page()
            title = stripped[2:].upper()
            pdf.current_section_title = title
            pdf.ln(5)
            pdf.set_fill_color(0, 40, 80)
            pdf.rect(0, pdf.get_y(), 210, 15, "F")
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(255, 255, 255)
            pdf.set_y(pdf.get_y() + 2)
            pdf.multi_cell(0, 10, pdf.clean_text(title), align="C")
            pdf.ln(5); pdf.set_text_color(0, 0, 0)
        elif stripped.startswith("## "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 15)
            pdf.set_text_color(0, 60, 120)
            pdf.multi_cell(0, 8, pdf.clean_text(line[3:]))
        elif stripped.startswith("### "):
            if "Key Features" in line: pdf.add_page()
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 7, pdf.clean_text(line[4:]))
        elif stripped.startswith("- "):
            pdf.draw_bullet(line[2:])
        elif stripped:
            if any(op in stripped for op in [" = ", " + ", " @ ", " / "]) and len(stripped) < 100:
                pdf.draw_code_box([stripped])
            else:
                pdf.set_font("Helvetica", "", 10.5)
                pdf.set_text_color(40, 40, 40)
                pdf.set_x(10)
                pdf.multi_cell(0, 5, pdf.clean_text(line))
                pdf.ln(0.5)

    out = os.path.join(os.path.dirname(__file__), "NOVA_v2.0_Technical_Manual.pdf")
    pdf.output(out)
    print(f"[OK] Master Manual: {out}")

if __name__ == "__main__":
    generate_manual()
