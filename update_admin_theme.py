# Update admin.html
with open('admin.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("'#FF263F'", "'#2563FF'")
text = text.replace("'#710B18'", "'#153EBD'")
text = text.replace("'#542032'", "'#153EBD'")
text = text.replace('#FF263F', '#2563FF')
text = text.replace('#ff263f', '#2563FF')
text = text.replace('#710B18', '#153EBD')
text = text.replace('#710b18', '#153EBD')
text = text.replace('#542032', '#153EBD')
text = text.replace('#ffdad8', '#E0F2FF')
text = text.replace('#ff455b', '#00A3FF')
text = text.replace('rgba(255, 38, 63,', 'rgba(37, 99, 255,')
text = text.replace('rgba(255,38,63,', 'rgba(37,99,255,')

with open('admin.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated admin.html successfully')
