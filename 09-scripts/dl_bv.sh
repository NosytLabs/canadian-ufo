#!/bin/zsh
# Fetch the Canada FOIA volumes and the CIRVIS compilation from the public
# mirrors. The output is a build input, not a deliverable: it is gitignored and
# the site links to the same URLs, so nothing here is published directly.
#
# The download is checked three ways before a file is accepted, because the
# failure mode here is silent. curl without --fail writes the 404 body to the
# target and still exits 0, and the -s test on the next run then skips the file
# forever -- so one bad fetch left an HTML error page cached under a .pdf name
# and nothing in the build could tell. curl -f, a %PDF magic check, and writing
# to .part then renaming together mean a partial or error body never becomes a
# file that looks finished.
set -e
HERE=${0:A:h}
ROOT=${HERE:h}
cd "$ROOT/03-declassified" || exit 1
mkdir -p canufodoc cirvis
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# First four bytes of a real PDF. An HTML error page fails this.
is_pdf() { [[ "$(head -c 4 "$1" 2>/dev/null)" == "%PDF" ]]; }

# A file already on disk is only trusted if it is a PDF, not just non-empty.
usable() { [[ -s $1 ]] && is_pdf "$1"; }

fetch() {
  local url=$1 dest=$2
  local part="${dest}.part"
  rm -f "$part"
  if ! /usr/bin/curl -fsSL --retry 3 --retry-delay 2 --max-time 600 -A "$UA" -o "$part" "$url"; then
    print -u2 "  curl failed: $url"
    rm -f "$part"
    return 1
  fi
  if ! is_pdf "$part"; then
    print -u2 "  not a PDF (first bytes: $(head -c 40 "$part" | tr -d '\0' | tr '\n' ' '))"
    rm -f "$part"
    return 1
  fi
  # Rename last so the .pdf name only ever appears on a complete, valid file.
  mv "$part" "$dest"
  print "  $(stat -f%z "$dest") bytes"
}

failed=()
for i in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29; do
  case $i in
    01) p1=1;p2=300;; 02) p1=301;p2=600;; 03) p1=601;p2=900;; 04) p1=901;p2=1200;;
    05) p1=1201;p2=1500;; 06) p1=1501;p2=1800;; 07) p1=1801;p2=2100;; 08) p1=2101;p2=2400;;
    09) p1=2401;p2=2700;; 10) p1=2701;p2=3000;; 11) p1=3001;p2=3300;; 12) p1=3301;p2=3600;;
    # 13 ended at 3901 and 14 started at 3901, so page 3901 was fetched into two
    # files. build_site_data.py parses the range back out of the filename to
    # build the release index, which then counted 3901 twice against a stated
    # 8,759-page series. Every other boundary is p2_prev+1; 13 was not.
    13) p1=3601;p2=3900;; 14) p1=3901;p2=4200;; 15) p1=4201;p2=4500;; 16) p1=4501;p2=4800;;
    17) p1=4801;p2=5100;; 18) p1=5101;p2=5400;; 19) p1=5401;p2=5700;; 20) p1=5701;p2=6000;;
    21) p1=6001;p2=6300;; 22) p1=6301;p2=6600;; 23) p1=6601;p2=6900;; 24) p1=6901;p2=7200;;
    25) p1=7201;p2=7500;; 26) p1=7501;p2=7800;; 27) p1=7801;p2=8100;; 28) p1=8101;p2=8400;;
    29) p1=8401;p2=8759;;
  esac
  f="canufodoc/CanUFODoc_${i}_pages_${p1}-${p2}.pdf"
  if usable "$f"; then print "skip $i"; continue; fi
  # A file that is present but not a PDF is a cached error body. Say so rather
  # than skipping it silently, then re-fetch over it.
  [[ -e $f ]] && print -u2 "  replacing $f: present but not a PDF"
  u="https://documents.theblackvault.com/documents/ufos/canada/Canada%20-%20FOIA%20Part%20${i}%20-%20Pages%20${p1}-${p2}.pdf"
  print "$i pages $p1-$p2"
  fetch "$u" "$f" || failed+=("$i")
  sleep 1
done

print "cirvis"
c="cirvis/CIRVIS-Canada-2010-2019.pdf"
if usable "$c"; then
  print "skip cirvis"
else
  fetch "https://documents2.theblackvault.com/documents/ufos/CIRVIS--Canada-2010-2019.pdf" "$c" \
    || failed+=("cirvis")
fi

if (( ${#failed} )); then
  print -u2 "FAILED: ${(j:, :)failed}"
  print -u2 "Delete any .part files and re-run. Nothing incomplete was kept."
  exit 1
fi
print DONE
