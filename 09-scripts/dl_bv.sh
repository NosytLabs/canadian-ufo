#!/bin/zsh
cd /Users/tyson/canadian-ufo-research/03-declassified || exit 1
mkdir -p canufodoc cirvis
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
for i in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29; do
  case $i in
    01) p1=1;p2=300;; 02) p1=301;p2=600;; 03) p1=601;p2=900;; 04) p1=901;p2=1200;;
    05) p1=1201;p2=1500;; 06) p1=1501;p2=1800;; 07) p1=1801;p2=2100;; 08) p1=2101;p2=2400;;
    09) p1=2401;p2=2700;; 10) p1=2701;p2=3000;; 11) p1=3001;p2=3300;; 12) p1=3301;p2=3600;;
    13) p1=3601;p2=3901;; 14) p1=3901;p2=4200;; 15) p1=4201;p2=4500;; 16) p1=4501;p2=4800;;
    17) p1=4801;p2=5100;; 18) p1=5101;p2=5400;; 19) p1=5401;p2=5700;; 20) p1=5701;p2=6000;;
    21) p1=6001;p2=6300;; 22) p1=6301;p2=6600;; 23) p1=6601;p2=6900;; 24) p1=6901;p2=7200;;
    25) p1=7201;p2=7500;; 26) p1=7501;p2=7800;; 27) p1=7801;p2=8100;; 28) p1=8101;p2=8400;;
    29) p1=8401;p2=8759;;
  esac
  f="canufodoc/CanUFODoc_${i}_pages_${p1}-${p2}.pdf"
  if [[ -s $f ]]; then echo "skip $i"; continue; fi
  u="https://documents.theblackvault.com/documents/ufos/canada/Canada%20-%20FOIA%20Part%20${i}%20-%20Pages%20${p1}-${p2}.pdf"
  /usr/bin/curl -sSL --max-time 300 -A "$UA" -o "$f" "$u"
  echo "$i -> $(stat -f%z "$f" 2>/dev/null) bytes"
  sleep 1
done
/usr/bin/curl -sSL --max-time 600 -A "$UA" -o cirvis/CIRVIS-Canada-2010-2019.pdf "https://documents2.theblackvault.com/documents/ufos/CIRVIS--Canada-2010-2019.pdf"
echo "cirvis -> $(stat -f%z cirvis/CIRVIS-Canada-2010-2019.pdf 2>/dev/null)"
echo DONE
