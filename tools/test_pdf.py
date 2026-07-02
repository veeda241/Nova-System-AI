import os
from fpdf import FPDF

# Simple script to check if FPDF creates content correctly
pdf = FPDF()
pdf.add_page()
pdf.set_font("Helvetica", size=12)
pdf.cell(200, 10, txt="TEST CONTENT - PAGE 1", ln=True, align='C')
pdf.multi_cell(0, 10, txt="This is a test of the multi_cell function to see how much space it takes in the final file.")
pdf.add_page()
pdf.cell(200, 10, txt="TEST CONTENT - PAGE 2", ln=True, align='C')
pdf.output("test_output.pdf")
print(f"Test PDF Size: {os.path.getsize('test_output.pdf')} bytes")
