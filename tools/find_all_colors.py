import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

print("--- GRADIENTS ---")
for m in re.finditer(r'linear-gradient\([^;]+?\)', text):
    print(m.group(0))

for m in re.finditer(r'radial-gradient\([^;]+?\)', text):
    print(m.group(0))

for m in re.finditer(r'bg-gradient-to-[a-z0-9]+[^\"\']*', text):
    print(m.group(0))

print("\n--- INLINE STYLES WITH COLOR ---")
for m in re.finditer(r'style="[^"]*?(?:color|background|border|shadow|fill|stroke)[^"]*?"', text):
    print(m.group(0))

print("\n--- SVG COLOR ATTRIBUTES ---")
for m in re.finditer(r'(?:fill|stroke)="[^"]*?"', text):
    if '#' in m.group(0) or 'rgb' in m.group(0):
        print(m.group(0))

print("\n--- BUTTONS & CTAS WITH RED/PINK ---")
for m in re.finditer(r'<(?:button|a)[^>]*?(?:#FF263F|#ff263f|primary|#710B18|#542032|gradient)[^>]*?>', text):
    print(m.group(0)[:140])

