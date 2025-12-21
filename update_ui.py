#!/usr/bin/env python3
"""Update nova_ble.py with new multi-page mobile UI - Fixed Version."""

# Read the new UI
with open('nova_ble_ui.html', 'r', encoding='utf-8') as f:
    new_html = f.read()

# Read nova_ble.py
with open('nova_ble.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the HTML start
start_marker = "MOBILE_UI_HTML = '''"
start_idx = content.find(start_marker)

# Find the class definition
class_marker = "class BleServer:"
class_idx = content.rfind(class_marker)

if start_idx == -1:
    print("ERROR: Could not find MOBILE_UI_HTML")
    exit(1)
    
if class_idx == -1:
    print("ERROR: Could not find BleServer class")
    exit(1)

# Get the part before MOBILE_UI_HTML (imports etc)
header = content[:start_idx]

# Get the part from BleServer class onwards
footer = content[class_idx:]

# Build new content
new_content = header + "MOBILE_UI_HTML = '''" + new_html + "'''\n\n\n" + footer

# Write back
with open('nova_ble.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✓ Updated nova_ble.py with multi-page UI!")
print(f"  Header: {len(header)} bytes")
print(f"  New HTML: {len(new_html)} bytes")
print(f"  Footer: {len(footer)} bytes")
print(f"  Total: {len(new_content)} bytes")
