from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
root=Path(__file__).resolve().parent.parent
page=root/'portfolio/social.html'
text=page.read_text(encoding='utf-8').replace('title="CH Weather Instagram profile" loading=', 'title="CH Weather Instagram profile" scrolling="no" loading=')
text=text.replace('../assets/styles.css"', '../assets/styles.css?v=instagram-frame-3"')
page.write_text(text,encoding='utf-8')
files=[root/'index.html',root/'README.md',*root.glob('portfolio/*.html'),*root.glob('assets/*'),root/'output/pdf/christopher-horne-resume-placeholder.pdf']
with ZipFile(root/'output/ch-weather-website.zip','w',ZIP_DEFLATED) as z:
    for p in files: z.write(p,p.relative_to(root).as_posix())
