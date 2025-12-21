#!/usr/bin/env python3
"""Fix the corrupted nova_ble.py file by removing duplicate BleServer class."""

with open('nova_ble.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the end of the proper HTML (ends with </html>''')
html_end = "</html>'''"
first_html_end = content.find(html_end)

if first_html_end == -1:
    print("Could not find HTML end marker")
    exit(1)

# Find where the proper BleServer class with docstring starts
proper_class = 'class BleServer:\n    """'
proper_class_idx = content.rfind(proper_class)

if proper_class_idx == -1:
    print("Could not find proper BleServer class")
    exit(1)

print(f"HTML ends at: {first_html_end}")
print(f"Proper BleServer at: {proper_class_idx}")

# The content we want:
# 1. Everything up to and including html_end
# 2. Two newlines
# 3. The proper BleServer class and everything after it

new_content = content[:first_html_end + len(html_end)] + "\n\n\n" + content[proper_class_idx:]

with open('nova_ble.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Fixed! Removed {proper_class_idx - first_html_end - len(html_end)} characters of garbage")
print(f"New file size: {len(new_content)} bytes")
