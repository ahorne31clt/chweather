from pathlib import Path
import re
root=Path(__file__).resolve().parent.parent
template=root/'assets/social-section.html'
section=template.read_text(encoding='utf-8')
section=section.replace('Weather. In the conversation.','Follow along with CH Weather.')
section=section.replace('<div class="instagram-window">','<div class="instagram-profile"><img src="../assets/ch-weather-logo.png" alt="CH Weather" width="64" height="64"><div><strong>CH Weather</strong><p>Student meteorologist Christopher Horne</p><a href="https://www.instagram.com/chweather/">Follow @chweather ↗</a></div></div><div class="instagram-window">')
template.write_text(section,encoding='utf-8')
old_page=(root/'portfolio/contact.html').read_text(encoding='utf-8')
heading='<section class="page-heading"><p class="eyebrow">06 / SOCIAL MEDIA</p><h1>Carolina weather.<br>Stay connected.</h1><p class="lede">Follow CH Weather for weather education, forecasts, and a closer look at the science behind what’s ahead.</p></section>'
new_page=re.sub(r'<main id="main" class="wrap">.*?</main>', '<main id="main" class="wrap">'+heading+section+'</main>',old_page,flags=re.S)
new_page=new_page.replace('<title>Contact | CH Weather</title>','<title>Social Media | CH Weather</title>').replace(' aria-current="page"','')
(root/'portfolio/social.html').write_text(new_page,encoding='utf-8')
for path in [root/'index.html',*root.glob('portfolio/*.html')]:
    text=path.read_text(encoding='utf-8')
    if path.name!='social.html':
        text=re.sub(r'<section class="section social-section".*?</section>\s*','',text,flags=re.S)
    if path.parent.name=='portfolio':
        nav='<a href="social.html"'+(' aria-current="page"' if path.name=='social.html' else '')+'>Social Media</a>'
        text=text.replace('<a href="contact.html"',nav+'<a href="contact.html"',1)
        if path.name=='contact.html': text=text.replace('06 / CONTACT','07 / CONTACT')
    else:
        text=text.replace('</nav>','<a href="portfolio/social.html">Social Media</a></nav>',1)
    path.write_text(text,encoding='utf-8')
builder=root/'build_site.py'
text=builder.read_text(encoding='utf-8').replace("('contact','Contact')]", "('social','Social Media'),('contact','Contact')]")
text=text.replace("    if home or slug in ('index', 'contact'):\n        body += (ROOT/'assets/social-section.html').read_text(encoding='utf-8')\n",'')
text=text.replace("nav = '<a href=\"portfolio/index.html\">Portfolio <span aria-hidden=\"true\">↗</span></a>'", "nav = '<a href=\"portfolio/index.html\">Portfolio <span aria-hidden=\"true\">↗</span></a><a href=\"portfolio/social.html\">Social Media</a>'")
text=text.replace("heading('06','CONTACT'", "heading('07','CONTACT'")
text=text.replace("('contact','Contact',contact)]:", "('social','Social Media',heading('06','SOCIAL MEDIA','Carolina weather.<br>Stay connected.','Follow CH Weather for weather education, forecasts, and a closer look at the science behind what’s ahead.')+(ROOT/'assets/social-section.html').read_text(encoding='utf-8')),('contact','Contact',contact)]:")
builder.write_text(text,encoding='utf-8')
readme=root/'README.md'
text=readme.read_text(encoding='utf-8').replace('appear on the landing page, portfolio overview, and contact page.','appear on the dedicated `portfolio/social.html` page.').replace('Instagram uses its native profile embed,','Instagram uses its native profile embed, framed to display its post grid beneath a charcoal profile header without recoloring the media,')
readme.write_text(text,encoding='utf-8')
