# Remove NAM

Upload these matching paths from the ZIP without deleting other files.
Run **Publish latest weather website** to remove old NAM artifacts from the published manifest. The next **Scheduled weather models** run refreshes GFS and HRRR only. Old files need no manual deletion; they are no longer referenced or packaged.

Changed source files:

- models/index.html
- models/__main__.py
- assets/models.js
- assets/mos.js
- .github/workflows/models.yml
- scripts/collect_publication.py
- scripts/merge_models.py
- tests/test_independent_publication.py
- tests/test_model_selection.py
- tests/test_packaging.py
- README.md
- docs/MODELS.md

NAM is removed from the map selector, command-line model choices, scheduler, publisher, local manifests and MOS choices. Low-level legacy decoding remains for compatibility tests; no active job requests it.
