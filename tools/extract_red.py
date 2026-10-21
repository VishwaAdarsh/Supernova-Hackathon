import re

with open('index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

red_hexes = [
    '#FF263F', '#ff263f', '#710B18', '#542032', '#ffdad8', '#ffb3b0', '#ffb4ab',
    '#ec627f', '#5a001f', '#93001b', '#8a1638', '#871e26', '#ffb2bd', '#ffb3b1',
    '#ffc0cc', '#aa091e', '#fff0f1', '#ff718e', '#93000a', '#5b000d', '#670212',
    '#400013', '#690005', '#bf0026', '#680010', '#ffdad6', '#ff9e9c', '#e8bcba',
    '#2a0e14', '#ff5359', '#341722', '#17080f', '#ff263f10', '#ae8785'
]

results = []
for i, line in enumerate(lines):
    matched = []
    line_lower = line.lower()
    for h in red_hexes:
        if h.lower() in line_lower:
            matched.append(h)
    if any(k in line_lower for k in ['rgba(255,', 'rgba(236,', 'rgb(175,', 'rgb(118,', 'rgb(148,', 'rgb(198,', 'rgba(165,', 'rgba(220,', 'rgba(242,']):
        matched.append('red-rgb')
    if matched:
        results.append((i+1, matched, line.strip()))

print(f"Total lines with red/pink accents: {len(results)}")
with open('red_occurrences.txt', 'w', encoding='utf-8') as rf:
    for num, tags, text in results:
        rf.write(f"L{num} [{','.join(tags)}]: {text}\n")
print("Written to red_occurrences.txt")
