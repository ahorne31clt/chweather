# Portfolio project update

## Upload to GitHub

Extract `output/ch-weather-portfolio-projects-update.zip`. Open the repository main page, choose Add file > Upload files, then drag the extracted **assets**, **portfolio**, **scripts**, **tests**, and **docs** folders into the upload area. Keep folder paths intact. Commit the replacements to main. Do not upload the ZIP itself or delete the existing site. No workflow changes or new credentials are required. The existing publish workflow handles the static-site update.

## Exact changed and added paths

Replaced:
- portfolio/index.html
- portfolio/projects.html
- scripts/package_site.py
- scripts/package_github.py
- tests/test_packaging.py

Added:
- portfolio/gis-tornado-shelters.html
- portfolio/norman-tornado-environments.html
- portfolio/charlotte-land-cover.html
- assets/project-detail.css
- assets/project-viewer.js
- docs/PORTFOLIO-PROJECTS.md

Added project assets (all included in the update ZIP):
- assets/projects/tornado-shelter-access/: map.pdf, report.pdf, map-preview.webp, cover.webp, slides.json
- assets/projects/norman-tornado-environments/: slides.pdf, slide-01.webp through slide-13.webp, cover.webp, slides.json
- assets/projects/charlotte-land-cover/: slides-web.pdf, slide-01.webp through slide-56.webp, cover.webp, slides.json

## Content and file sizes

The GIS project includes the supplied report and map. The Norman tornado project includes the supplied 13-slide presentation. The Charlotte land-cover project credits Christopher Horne and Jenna Bess and includes all 56 slides. Descriptions summarize the submitted coursework and identify important limitations; these are historical projects, not current forecasts or a live shelter directory.

The supplied 59.4 MB Charlotte presentation was optimized to 22.1 MB. All 56 pages retain their extracted text and seven reference links. The original in Downloads was not changed. Each PDF included in the upload is below 25 MB. Slide galleries load lightweight WebP previews rather than downloading the PDFs on page load.

To keep the Pages build below 1 GB, three larger PDFs are stored in the public repository and linked directly from GitHub: tornado-shelter-access/map.pdf, norman-tornado-environments/slides.pdf, and charlotte-land-cover/slides-web.pdf. Upload the two packaging scripts along with the assets: they exclude those PDFs from the Pages deployment but keep them in source and portable ZIP exports. The short GIS report remains on Pages. Localhost previews use local PDF copies automatically.

## Preview

http://127.0.0.1:8000/portfolio/projects.html

The local preview is ready; GitHub changes take effect after uploading and the publish workflow completes.
