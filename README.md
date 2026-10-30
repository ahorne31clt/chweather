# CH Weather

Static HTML, CSS, and JavaScript. No build system, account, or paid service required.

## Preview

Open `index.html` directly, or run `python -m http.server 8000` in this folder and visit http://localhost:8000. The portfolio begins at `/portfolio/` when served.

## Edit

- `index.html`: main CH Weather placeholder.
- `portfolio/index.html`: portfolio overview.
- Other `portfolio/*.html` files: individual portfolio pages. All page content is plain HTML.
- `assets/styles.css`: colors, typography, layout, responsive styling, and motion.
- `assets/site.js`: mobile navigation and coursework filters.
- `assets/ch-weather-logo.png`: original logo, copied without modification.
- `assets/contours.svg`: decorative contours, not weather observations or model data.
- `output/pdf/christopher-horne-resume-placeholder.pdf`: replace with the finished résumé and update the link/label in `portfolio/contact.html`.

Navigation and footer markup are present in each HTML file so pages work without JavaScript. Update each page when changing navigation. Optional Google Fonts load Barlow and Barlow Condensed; local system fonts work when offline.

`build_site.py` is the initial generation script and requires reportlab. It is not needed to edit, preview, or host this site. Avoid rerunning it after manual HTML edits; it rewrites the generated pages and placeholder PDF.

## Social embeds

Instagram @chweather, X @chornewx, and YouTube @chornewx appear on the dedicated `portfolio/social.html` page. Instagram uses its native profile embed, framed to display its post grid beneath a charcoal profile header without recoloring the media, X its official timeline widget, and YouTube the verified channel introduction video. The embeds depend on platform availability, public-account/embed settings, and the visitor's browser. Direct profile links remain available. No paid feed service or API keys are needed. YouTube video ID: `ytZDTcEJkys`; verified channel ID: `UCu67Ke4SnF9scSaNyT9anPQ`. Replace the player URL when you want to feature another video. `assets/social-section.html` is the generation template; the published HTML contains its markup directly.

## Adding projects

Replace the planned entries in `portfolio/projects.html` with real titles, dates, descriptions, and links. Put PDFs/slides in a new `assets/projects/` folder. Keep the Coming soon label until an actual artifact is available. Interactive projects can live in their own subfolders.

## Hosting later

Upload `index.html`, `assets/`, `portfolio/`, and `output/pdf/` to any static host. No subdomain is required. Keep the directory structure intact. `/portfolio/` is a path on the same domain. No current weather feed, analytics, form service, or credentials are configured.

The transcript is deliberately not included in the website files. Grades, GPA, birth date, and withdrawn/failed coursework are not published. Courses currently being repeated appear only in the current category. Spring 2027 courses are planned, not confirmed enrollment.
