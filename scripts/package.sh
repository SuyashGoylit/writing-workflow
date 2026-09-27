#!/usr/bin/env bash
# Zip each skill for upload to claude.ai (Settings → Capabilities → Skills → Upload).
# Each zip contains the skill folder at its root, as claude.ai expects.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/dist"
cd "$ROOT/skills"
for dir in */; do
  name="${dir%/}"
  rm -f "$ROOT/dist/$name.zip"
  zip -rq "$ROOT/dist/$name.zip" "$name" -x '*/__pycache__/*' '*.pyc'
  echo "built dist/$name.zip"
done
