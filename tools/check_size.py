from fpdf import FPDF
import os

pdf_path = r"c:\hackathon\Gemini_CLI\Nova-System-AI\docs\NOVA_v2.0_Technical_Manual.pdf"
if os.path.exists(pdf_path):
    print(f"File Size: {os.path.getsize(pdf_path)} bytes")
    # We can't easily count pages without another lib, but 5KB is very small for multiple pages.
else:
    print("File not found")
