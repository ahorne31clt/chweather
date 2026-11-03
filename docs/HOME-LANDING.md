# CH Weather landing page

The homepage introduces CH Weather and provides four organized directories:
Forecasts, Live Weather, Model Guidance, and Seasons & Climate. An introduction
to Christopher, portfolio links and social channels follow. Large forecast maps
and live warning counters are kept on their dedicated pages. The homepage makes
no weather API requests and does not depend on generated forecast files loading.

Replace these two paths in the GitHub repository, preserving their locations:

- `index.html` — the homepage, at the repository root.
- `assets/home.css` — landing-page styling, inside `assets/`.

This guide is included as `docs/HOME-LANDING.md`. Existing shared styles, logo,
headshot, navigation script and site script are reused. No other pages or model
generation files need replacing. Do not upload the homepage into `alerts/`.

Uploading these files triggers **Publish latest weather website** through its
HTML/assets paths. You can also run that workflow manually. Weather generators
do not need rerunning for this presentation change.

The local `_site/` preview is updated. Desktop and mobile checks confirmed four
directory groups, loaded logo/headshot, working local targets, no JavaScript page
errors, and no horizontal overflow at 390 px width.
