#!/bin/sh
# Registers this project's local mnema store as a vault on the root store
# (~/.mnema), so questions asked against root ("mnema ask ...", no --store
# needed) fold in this project's memories alongside doctrine, the full
# e-library, and every other registered project.
#
# The project store itself stays lean: it holds only this project's own
# writes (`mnema remember`) and mounts nothing of its own -- doctrine and
# the library live once, on root, not copied into every project.
#
# Bootstraps root (doctrine + library) on first use if it doesn't exist yet.
set -eu

PROJECT_STORE="${1:-./Resources/.mnema}"
PROJECT_NAME="${2:-$(basename "$(cd "$(dirname "$PROJECT_STORE")/.." && pwd)")}"
ROOT="$HOME/.mnema"
TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$ROOT" ]; then
    echo "root store not found at $ROOT -- bootstrapping (doctrine + library, one-time)" >&2
    mnema --store "$ROOT" init
    mnema --store "$ROOT" vault add "$HOME/MyProjects/MyPython/.mnema-doctrine" --name doctrine
    "$TEMPLATE_DIR/mount-library.sh" "$ROOT"
fi

abs_project_store="$(cd "$PROJECT_STORE" && pwd)"
mnema --store "$ROOT" vault add "$abs_project_store" --name "project-$PROJECT_NAME"
