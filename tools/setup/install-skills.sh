#!/usr/bin/env bash
# Install the third-party agent skills this project's art pipeline uses.
#
# Run once per machine (or per fresh container):
#   bash tools/setup/install-skills.sh
#
# These are NOT vendored into the repo. img2threejs is 4.9 MB of someone else's
# Apache-2.0 project; committing a copy would fork it silently and it would
# drift from upstream the first time they fix something. .claude/skills/ is
# gitignored and this script is the reproducible way back.
#
# Like everything in tools/, this is an authoring-time step: the game does not
# call it, the build does not need it, and `npm test` passes without it.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEST="$ROOT/.claude/skills"
mkdir -p "$DEST"

install_skill() {
  local name="$1" url="$2"
  if [ -d "$DEST/$name/.git" ]; then
    echo "updating $name"
    git -C "$DEST/$name" pull --ff-only --quiet
  else
    echo "cloning  $name"
    rm -rf "${DEST:?}/$name"
    git clone --depth 1 --quiet "$url" "$DEST/$name"
  fi
  echo "         $DEST/$name"
}

# Reads a 2D reference image and rebuilds it as a code-only procedural Three.js
# model. Staged: intake -> spec -> build passes -> screenshot review. Python
# 3.10+ standard library only, no third-party deps.
install_skill img2threejs https://github.com/hoainho/img2threejs.git

echo
echo "done. Skills load on the next session in this directory."
