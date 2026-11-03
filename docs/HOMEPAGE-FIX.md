# Homepage layout fix

Replace `index.html` at the repository root with the file in this ZIP.
Do not upload it into `alerts/` or replace `alerts/index.html`.

The homepage introduction and logo now appear first. Redundant announcement
banners were removed; the compact NWS warning summary remains below the
introduction. Links to solar optics, seasonal guidance and radar were added
to the existing weather directory. The dedicated warnings page is unchanged.

Uploading the HTML change triggers **Publish latest weather website**.
You can also run that workflow manually to publish immediately. The local preview under `_site/index.html` is already updated.
No weather data generation is necessary for this HTML change itself.

Changed source: `index.html`. Added documentation: `docs/HOMEPAGE-FIX.md`.
