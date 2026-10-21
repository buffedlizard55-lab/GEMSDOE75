#!/usr/bin/env bash
# Download the DOE GEMS Prize Challenge data into data/raw/.
#
# HONESTY NOTICE (read this before trusting anything this script prints):
# This sandbox's outbound network is restricted to github.com,
# codeload.github.com, api.github.com, registry.npmjs.org, pypi.org and
# files.pythonhosted.org. It CANNOT reach www.drivendata.org (login-walled
# anyway), dropbox.com, gdr.openei.org, usgs.gov, or sciencebase.gov. That
# was re-verified on 2026-10-21 with a direct curl to each host (all timed
# out / connection-refused). So when this script runs *inside the agent
# sandbox* it will correctly report every competition-data host as
# unreachable -- that is not a bug, it is the actual state of this
# environment, and it is why this repository ships code and tests built
# entirely against synthetic data (see tests/).
#
# Run this script on a machine with normal unrestricted internet access
# (your laptop, a DrivenData-provided notebook environment, GitHub Actions,
# etc.), not inside this sandbox, to actually fetch the data.
set -euo pipefail

OUT_DIR="${1:-data/raw}"
mkdir -p "$OUT_DIR"

echo "== DOE GEMS Prize Challenge data fetch =="
echo "Target directory: $OUT_DIR"
echo

check_host() {
  local host="$1"
  if curl -sS -m 8 -o /dev/null -w '%{http_code}' "https://$host" 2>/dev/null | grep -qE '^[0-9]+$'; then
    echo "  reachable: $host"
    return 0
  else
    echo "  UNREACHABLE from this machine: $host"
    return 1
  fi
}

echo "-- Step 1: reachability check --"
check_host "www.drivendata.org" || true
check_host "www.dropbox.com" || true
echo

cat <<'EOF'
-- Step 2: official competition data (requires a DrivenData login) --
The organizer's competition data page requires an authenticated session;
there is no public/anonymous download URL for the primary files. Verified
2026-10-21 by fetching https://www.drivendata.org/competitions/306/competition-doe-gems/data/
unauthenticated, which redirects to /accounts/login/?next=/competitions/306/competition-doe-gems/data/ .

Manual steps (one-time, ~2 minutes):
  1. Log in at https://www.drivendata.org/accounts/login/
  2. Open   https://www.drivendata.org/competitions/306/competition-doe-gems/data/
  3. Download the four files listed there and save them exactly as:
       data/raw/training_features.tif   (a.k.a. numeric_features.tif in the
                                          reference solution notebook)
       data/raw/labels.tif
       data/raw/sample_submission.tif
       data/raw/1m_DEM_links.csv

A community-shared Dropbox mirror of some of the same files has also been
referenced in this project's working notes (unofficial convenience copies,
not a substitute for verifying against the organizer's own page):
  GEMS_96647.pdf            https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf
  example_submission.tif    https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif
  existing_faults.tif       https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif
  gems-geodawn-numerical-features.tif
                             https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif
  Digital-elevation-model-links-JSON.pdf
                             https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf
These are third-party-hosted mirrors, not organizer infrastructure --
verify file hashes/content against the real organizer page once you can
reach it, and flag any mismatch.

-- Step 3: free, official external data used by our ranked hypotheses --
(see docs/hypotheses.html / docs/data/hypotheses.json for which hypothesis
needs which file)
EOF

mkdir -p "$OUT_DIR/external"

declare -A EXTERNAL_SOURCES=(
  ["gdr1391_volcanics"]="https://gdr.openei.org/files/1391/great_basin_q_volcanics.zip"
  ["gdr1391_2m_temp_probe"]="https://gdr.openei.org/files/1391/2m_temperature_probe_INGENIOUS_regional_data.zip"
  ["gdr1391_paleo_geothermal"]="https://gdr.openei.org/files/1391/paleo_geothermal_regional.zip"
  ["gdr1391_seismicity"]="https://gdr.openei.org/files/1391/seismicity_INGENIOUS_regional_data.zip"
  ["gdr1391_wellspring"]="https://gdr.openei.org/files/1391/wellspringdata.gdb.zip"
  ["gdr1391_geodetics"]="https://gdr.openei.org/files/1391/geodetics_INGENIOUS_regional_data.zip"
)

for name in "${!EXTERNAL_SOURCES[@]}"; do
  url="${EXTERNAL_SOURCES[$name]}"
  dest="$OUT_DIR/external/$(basename "$url")"
  echo "Fetching $name <- $url"
  if curl -fsSL -m 60 -o "$dest" "$url"; then
    echo "  OK -> $dest ($(du -h "$dest" | cut -f1))"
  else
    echo "  FAILED: $url is unreachable from this machine. Download it manually and place it at $dest"
  fi
done

echo
echo "Done. Next step: python scripts/prepare_data.py"
