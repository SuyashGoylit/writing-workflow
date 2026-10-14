#!/usr/bin/env bash
# Zip each skill for upload to claude.ai (Settings → Capabilities → Skills → Upload).
# Each zip contains the skill folder at its root, as claude.ai expects.
# Folders starting with "_" hold shared files, not skills: the case study skills get
# skills/_shared/* copied into their scripts/ folder, plus the blog banned-phrase list,
# and case-study-verify also gets case-study-lp/template.md (its fixed-copy reference).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/dist"
cd "$ROOT/skills"
for dir in */; do
  name="${dir%/}"
  [[ "$name" == _* ]] && continue
  stage="$(mktemp -d)"
  cp -r "$name" "$stage/"
  if [[ "$name" == case-study-* ]]; then
    mkdir -p "$stage/$name/scripts"
    cp _shared/*.py _shared/client_names.txt "$stage/$name/scripts/"
    cp blog-audit/banned_phrases.txt "$stage/$name/"
  fi
  if [[ "$name" == case-study-verify ]]; then
    cp case-study-lp/template.md "$stage/$name/"
  fi
  rm -f "$ROOT/dist/$name.zip"
  (cd "$stage" && zip -rq "$ROOT/dist/$name.zip" "$name" -x '*/__pycache__/*' '*.pyc')
  rm -rf "$stage"
  echo "built dist/$name.zip"
done
