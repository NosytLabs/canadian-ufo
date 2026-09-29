#!/bin/sh
# Rebuild the site and stage it for GitHub Pages.
#
# GitHub Pages only serves from / or /docs, and the archive's 1 GB of PDFs must
# not be committed, so the authored site in site/ is copied to docs/ for
# publishing. Run this before every push that changes the site.
set -e
cd "$(dirname "$0")/.."

echo "-> building data"
python3 09-scripts/build_site_data.py
python3 09-scripts/build_aurora_data.py

echo "-> generating pages"
python3 09-scripts/generate_pages.py

echo "-> checking links"
# Do not pipe this: a pipeline reports head's exit status, so a broken link
# would sail through set -e and still publish.
python3 09-scripts/check_links.py

echo "-> staging to docs/"
rm -rf docs
mkdir -p docs
cp -R site/. docs/
find docs -name '.DS_Store' -delete

echo "-> staged $(find docs -type f | wc -l | tr -d ' ') files, $(du -sh docs | cut -f1)"
echo "   publish: https://nosytlabs.github.io/canadian-ufo/"
