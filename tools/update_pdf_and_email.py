# Update pdf_generator.py
with open('pdf_generator.py', 'r', encoding='utf-8') as f:
    pdf_text = f.read()

pdf_text = pdf_text.replace('Main Crimson Border', 'Main Electric Blue Border')
pdf_text = pdf_text.replace("HexColor('#ff263f')", "HexColor('#2563FF')")
pdf_text = pdf_text.replace("HexColor('#542032')", "HexColor('#153EBD')")

with open('pdf_generator.py', 'w', encoding='utf-8') as f:
    f.write(pdf_text)
print('Updated pdf_generator.py successfully')

# Update email_service.py
with open('email_service.py', 'r', encoding='utf-8') as f:
    email_text = f.read()

email_text = email_text.replace('#FF263F', '#2563FF')
email_text = email_text.replace('#ff263f', '#2563FF')
email_text = email_text.replace('#542032', '#153EBD')
email_text = email_text.replace('rgba(255, 38, 63,', 'rgba(37, 99, 255,')
email_text = email_text.replace('rgba(255,38,63,', 'rgba(37,99,255,')

with open('email_service.py', 'w', encoding='utf-8') as f:
    f.write(email_text)
print('Updated email_service.py successfully')
