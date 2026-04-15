# PDF Folder Structure (Germany demo)

Canonical layout (Germany-only):

- `scripts/seed_data/pdfs/by-industry/<industry>/<company-slug>/<year>/<report-type>/`
- `scripts/seed_data/pdfs/_inbox/` for unsorted downloads
- `scripts/seed_data/pdfs/_seed-ready-flat/` for script-ready files

Recommended report-type folders:

- `annual-report`
- `financial-report`
- `sustainability-report`
- `integrated-report`
- `other`

## Important for seed script

`python scripts/seed_german_demo.py` only auto-detects files at:

- `scripts/seed_data/pdfs/<slug>.pdf`

So when you finalize a company PDF for seeding, copy/symlink one final file to the flat path above.
Example:

```bash
cp scripts/seed_data/pdfs/by-industry/energy/rwe-2024/2024/annual-report/*.pdf    scripts/seed_data/pdfs/rwe-2024.pdf
```
