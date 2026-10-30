from pathlib import Path
root=Path(__file__).resolve().parent.parent
section=(root/'assets/social-section.html').read_text(encoding='utf-8')
for path in [root/'index.html',*root.glob('portfolio/*.html'),root/'build_site.py']:
    text=path.read_text(encoding='utf-8').replace('https://x.com/chweather','https://x.com/chornewx')
    text=text.replace("('03','X','@chweather'", "('03','X','@chornewx'")
    text=text.replace('<h3>X</h3><p>@chweather</p>','<h3>X</h3><p>@chornewx</p>')
    if path.name=='build_site.py':
        text=text.replace("    pre = '' if home else '../'", "    if home or slug in ('index', 'contact'):\n        body += (ROOT/'assets/social-section.html').read_text(encoding='utf-8')\n    pre = '' if home else '../'")
    elif path in [root/'index.html',root/'portfolio/index.html',root/'portfolio/contact.html']:
        text=text.replace('</main>',section+'</main>')
    path.write_text(text,encoding='utf-8')
