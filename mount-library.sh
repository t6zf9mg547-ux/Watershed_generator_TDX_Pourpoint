#!/bin/sh
# Mounts every shard of the e-library research corpus as a named vault on a
# mnema store. Shards are auto-discovered from the filesystem (each
# subdirectory of the library root that has a config.json), not a maintained
# list -- adding/removing shards under the library root needs no template
# change or re-run beyond calling this script again.
#
# This is a ROOT-level, one-time setup step, not a per-project one: the
# library (and doctrine) live on the root store (~/.mnema) only, and every
# project attaches to root as its own leaf vault instead of re-mounting the
# whole library itself. See register-project.sh for the per-project step.
set -eu

STORE="${1:-$HOME/.mnema}"
LIBRARY_ROOT="$HOME/.mnema-vaults/e-library"

if [ ! -d "$LIBRARY_ROOT" ]; then
    echo "no library root at $LIBRARY_ROOT -- nothing to mount" >&2
    exit 1
fi

# `mnema vault add` is idempotent for an exact (name, addr) repeat -- a
# genuine name collision against a DIFFERENT addr still errors, which is
# what we want. No need to pre-check `vault list` ourselves.
for shard in "$LIBRARY_ROOT"/*/; do
    [ -f "${shard}config.json" ] || continue
    base="$(basename "$shard")"
    case "$base" in
        *.pre-recompile) continue ;;   # stale recompile backup, not a live shard
    esac
    name="library-$base"
    mnema --store "$STORE" vault add "$shard" --name "$name"
done
