#!/usr/bin/env bash
# Fill in your identity everywhere and assemble the community app store.
#
# Usage:
#   GH_USER=yourname [DISPLAY_NAME="Your Name"] ./scripts/finalize.sh
#
# After this runs, see the printed next steps to build the image and publish.
set -euo pipefail

GH_USER="${GH_USER:?Set GH_USER to your GitHub username, e.g. GH_USER=octocat ./scripts/finalize.sh}"
DISPLAY_NAME="${DISPLAY_NAME:-$GH_USER}"

cd "$(dirname "$0")/.."

echo "Filling placeholders: GH_USER=$GH_USER  DISPLAY_NAME=$DISPLAY_NAME"
grep -rl "YOUR_GITHUB_USERNAME\|YOUR_NAME" \
  --include="*.yml" --include="*.md" . 2>/dev/null | while read -r f; do
  sed -i "s/YOUR_GITHUB_USERNAME/$GH_USER/g; s/YOUR_NAME/$DISPLAY_NAME/g" "$f"
  echo "  updated $f"
done

# Assemble the community app store (contents of umbrel/ become its repo root).
STORE_DIR="../floortrades-store"
echo "Assembling community store at $STORE_DIR"
rm -rf "$STORE_DIR"
cp -r umbrel "$STORE_DIR"

echo
echo "================  DONE — now run these two steps  ================"
echo
echo "1) Build the image locally on this machine (the only sudo step):"
echo "     sudo docker build -t ghcr.io/$GH_USER/floortrades:1.0.0 $(pwd)"
echo
echo "2) Publish the community store repo and add it to Umbrel:"
echo "     cd $STORE_DIR && git init -b main && git add . \\"
echo "       && git commit -m 'FloorTrades community app store v1.0.0'"
echo "     # create the repo on github.com named 'floortrades-store', then:"
echo "     git remote add origin https://github.com/$GH_USER/floortrades-store.git"
echo "     git push -u origin main"
echo
echo "   Then on Umbrel: Settings -> App Store -> Community App Stores -> Add"
echo "     https://github.com/$GH_USER/floortrades-store"
echo
echo "   (To share with others later, see PUBLISHING.md for the GHCR push.)"
echo "=================================================================="
