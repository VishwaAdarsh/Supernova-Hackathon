import re
import shutil

# Make sure backups exist
shutil.copyfile('index.html', 'index.html.bak')
shutil.copyfile('index.html', 'supernova.html.bak')

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Gradients
# Chrome wordmark ticket
content = content.replace(
    'linear-gradient(180deg, #ffffff 0%, #ffc0cc 45%, #ff263f 80%, #aa091e 100%)',
    'linear-gradient(180deg, #E0F2FF 0%, #00A3FF 45%, #2563FF 80%, #153EBD 100%)'
)

# Navbar Brand Wordmark
content = content.replace(
    'linear-gradient(90deg, #fff0f1 0%, #ff718e 45%, #ff263f 100%)',
    'linear-gradient(90deg, #E0F2FF 0%, #00A3FF 45%, #2563FF 100%)'
)

# Hero Title SUPERNOVA gradient
content = content.replace(
    'from-[#eae0e3] via-[#ffb3b0] to-[#ae8785]',
    'from-[#E0F2FF] via-[#00A3FF] to-[#2563FF]'
)

# Ambient glow backlights
content = content.replace(
    'from-[#FF263F]/15 via-[#710B18]/10 to-transparent',
    'from-[#2563FF]/15 via-[#153EBD]/10 to-transparent'
)
content = content.replace(
    'from-[#710B18]/25 to-transparent',
    'from-[#153EBD]/25 to-transparent'
)
content = content.replace(
    'from-[#FF263F]/15 via-[#542032]/20 to-transparent',
    'from-[#2563FF]/15 via-[#153EBD]/20 to-transparent'
)

# Arena 2 progress bar
content = content.replace(
    'from-[#710B18] to-tertiary-container',
    'from-[#153EBD] to-[#00E5FF]'
)

# Map repeating scanline
content = content.replace(
    '#ff263f10',
    '#2563FF10'
)

# Official ticket pass background radial gradient
content = content.replace(
    'radial-gradient(circle at 60% 40%, #1c0812 0%, #0a0407 100%)',
    'radial-gradient(circle at 60% 40%, #0B1B3D 0%, #09070A 100%)'
)

# 2. Binary skull canvas script updates
content = content.replace(
    'ctx.shadowColor = "rgba(255, 38, 63, 0.35)";',
    'ctx.shadowColor = "rgba(37, 99, 255, 0.35)";'
)
content = content.replace(
    'ctx.fillStyle = `rgba(255, 65, 95, ${effectiveAlpha * 0.90})`;',
    'ctx.fillStyle = `rgba(0, 229, 255, ${effectiveAlpha * 0.90})`;'
)
content = content.replace(
    'ctx.fillStyle = `rgba(165, 22, 42, ${effectiveAlpha * 0.78})`;',
    'ctx.fillStyle = `rgba(21, 62, 189, ${effectiveAlpha * 0.78})`;'
)
content = content.replace(
    'ctx.fillStyle = `rgba(220, 38, 65, ${effectiveAlpha * 0.85})`;',
    'ctx.fillStyle = `rgba(0, 163, 255, ${effectiveAlpha * 0.85})`;'
)
content = content.replace(
    'ctx.fillStyle = `rgba(242, 34, 60, ${effectiveAlpha * 0.88})`;',
    'ctx.fillStyle = `rgba(37, 99, 255, ${effectiveAlpha * 0.88})`;'
)

# Skull canvas comments & annotations
content = content.replace(
    'Restrained, elegant obsidian-crimson & burgundy palette:',
    'Restrained, elegant electric blue & cyan telemetry palette:'
)
content = content.replace('rgb(175, 26, 46)', 'rgb(37, 99, 255)')
content = content.replace('rgb(118, 16, 32)', 'rgb(21, 62, 189)')
content = content.replace('rgb(148, 24, 46)', 'rgb(0, 163, 255)')
content = content.replace('rgb(198, 36, 58)', 'rgb(0, 229, 255)')
content = content.replace('soft warm crimson', 'cyan highlight')
content = content.replace('deep wine', 'deep blue')
content = content.replace('shadow rose', 'bright electric blue')
content = content.replace('muted crimson', 'primary electric blue')
content = content.replace('Ambient cybernetic crimson glow', 'Ambient cybernetic electric blue glow')
content = content.replace('Luminous rose-crimson accent', 'Luminous cyan highlight accent')
content = content.replace('Rich deep wine', 'Rich deep blue')
content = content.replace('Warm vibrant crimson', 'Bright electric blue')
content = content.replace('Core electric crimson', 'Primary electric blue')

# 3. Drop shadows & Glows with rgba(255, 38, 63, ...) or rgba(255,38,63,...)
content = re.sub(r'rgba\(\s*255\s*,\s*38\s*,\s*63\s*,', 'rgba(37, 99, 255,', content)
content = re.sub(r'rgba\(255,38,63,', 'rgba(37,99,255,', content)
content = re.sub(r'rgba\(236,98,127,', 'rgba(0,163,255,', content)

# 4. Tailwind Theme configuration
# We update the red-toned tokens in tailwind.config
tailwind_token_map = {
    '"secondary-fixed": "#ffdad8"': '"secondary-fixed": "#E0F2FF"',
    '"on-primary-container": "#5b000d"': '"on-primary-container": "#E0F2FF"',
    '"outline-variant": "#542032"': '"outline-variant": "#153EBD"',
    '"on-secondary": "#670212"': '"on-secondary": "#00174c"',
    '"on-tertiary-fixed": "#400013"': '"on-tertiary-fixed": "#00174c"',
    '"primary": "#ffb3b0"': '"primary": "#00A3FF"',
    '"tertiary-container": "#ec627f"': '"tertiary-container": "#00E5FF"',
    '"primary-fixed": "#ffdad8"': '"primary-fixed": "#E0F2FF"',
    '"on-tertiary-container": "#5a001f"': '"on-tertiary-container": "#E0F2FF"',
    '"secondary-container": "#710B18"': '"secondary-container": "#153EBD"',
    '"surface-tint": "#ffb3b0"': '"surface-tint": "#00A3FF"',
    '"primary-fixed-dim": "#ffb3b0"': '"primary-fixed-dim": "#00A3FF"',
    '"on-primary-fixed-variant": "#93001b"': '"on-primary-fixed-variant": "#153EBD"',
    '"on-tertiary-fixed-variant": "#8a1638"': '"on-tertiary-fixed-variant": "#153EBD"',
    '"tertiary-fixed-dim": "#ffb2bd"': '"tertiary-fixed-dim": "#00E5FF"',
    '"on-secondary-fixed-variant": "#871e26"': '"on-secondary-fixed-variant": "#153EBD"',
    '"primary-container": "#FF263F"': '"primary-container": "#2563FF"',
    '"secondary-fixed-dim": "#ffb3b1"': '"secondary-fixed-dim": "#00E5FF"',
    '"on-surface-variant": "#e8bcba"': '"on-surface-variant": "#D6CBD0"',
    '"inverse-primary": "#bf0026"': '"inverse-primary": "#2563FF"',
    '"on-primary": "#680010"': '"on-primary": "#FFFFFF"',
    '"secondary": "#ffb3b1"': '"secondary": "#00E5FF"',
    '"tertiary": "#ffb2bd"': '"tertiary": "#00E5FF"',
    '"on-secondary-container": "#ff9e9c"': '"on-secondary-container": "#E0F2FF"',
}

for old_tok, new_tok in tailwind_token_map.items():
    content = content.replace(old_tok, new_tok)

# 5. Core Hex Replacements across markup & styles
# Note: #FF263F / #ff263f -> #2563FF
content = content.replace('#FF263F', '#2563FF')
content = content.replace('#ff263f', '#2563FF')

# #710B18 / #710b18 -> #153EBD
content = content.replace('#710B18', '#153EBD')
content = content.replace('#710b18', '#153EBD')

# #542032 -> #153EBD
content = content.replace('#542032', '#153EBD')

# #ffdad8 / #FFDAD8 -> #E0F2FF
content = content.replace('#ffdad8', '#E0F2FF')
content = content.replace('#FFDAD8', '#E0F2FF')

# Write output to supernova.html and index.html
with open('supernova.html', 'w', encoding='utf-8') as out_f:
    out_f.write(content)

with open('index.html', 'w', encoding='utf-8') as out_f:
    out_f.write(content)

print("Successfully generated supernova.html and updated index.html")
