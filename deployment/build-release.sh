#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_DIR="${1:-$ROOT_DIR/dist/release}"
COMMIT_SHA="${GITHUB_SHA:-$(git -C "$ROOT_DIR" rev-parse --short HEAD)}"

if [[ "$ARTIFACT_DIR" != /* ]]; then
    ARTIFACT_DIR="$ROOT_DIR/$ARTIFACT_DIR"
fi

if [[ ! "$COMMIT_SHA" =~ ^[[:xdigit:]]{7,40}$ ]]; then
    printf 'Invalid release identifier: %s\n' "$COMMIT_SHA" >&2
    exit 2
fi

STAGING_DIR="$(mktemp -d)"
cleanup() {
    rm -rf -- "$STAGING_DIR"
}
trap cleanup EXIT

cd "$ROOT_DIR"
npm run build:production

if [[ ! -d "$ROOT_DIR/dist/vd-pcibex/browser" ]]; then
    printf 'Angular browser output was not created.\n' >&2
    exit 1
fi

mkdir -p \
    "$STAGING_DIR/backend" \
    "$STAGING_DIR/release/backend/wheelhouse" \
    "$STAGING_DIR/release/frontend"
python3 -m build --no-isolation --wheel "$ROOT_DIR/server" --outdir "$STAGING_DIR/backend"
python3 -m pip download \
    --only-binary=:all: \
    --requirement "$ROOT_DIR/server/requirements.lock" \
    --dest "$STAGING_DIR/release/backend/wheelhouse"
python3 -m venv "$STAGING_DIR/smoke-venv"
"$STAGING_DIR/smoke-venv/bin/python" -m pip install \
    --no-index \
    --find-links "$STAGING_DIR/release/backend/wheelhouse" \
    --requirement "$ROOT_DIR/server/requirements.lock"
"$STAGING_DIR/smoke-venv/bin/python" -m pip install \
    --no-deps \
    "$STAGING_DIR"/backend/*.whl
"$STAGING_DIR/smoke-venv/bin/python" -c \
    "from pcibex_server.server import app; assert app is not None"
cp -a "$ROOT_DIR/dist/vd-pcibex/browser" "$STAGING_DIR/release/frontend/"
cp "$STAGING_DIR"/backend/*.whl "$STAGING_DIR/release/backend/"
cp "$ROOT_DIR/server/requirements.lock" "$STAGING_DIR/release/backend/"
printf '%s\n' "$COMMIT_SHA" > "$STAGING_DIR/release/COMMIT"

mkdir -p "$ARTIFACT_DIR"
ARTIFACT_PATH="$ARTIFACT_DIR/pcibex-release-$COMMIT_SHA.tar.gz"
tar -czf "$STAGING_DIR/release.tar.gz" -C "$STAGING_DIR/release" .

python3 "$ROOT_DIR/deployment/verify-release.py" "$STAGING_DIR/release.tar.gz"

mv "$STAGING_DIR/release.tar.gz" "$ARTIFACT_PATH"
(
    cd "$ARTIFACT_DIR"
    sha256sum "$(basename "$ARTIFACT_PATH")" > "$(basename "$ARTIFACT_PATH").sha256"
)
cp "$ROOT_DIR/deployment/install-release.py" "$ARTIFACT_DIR/install-release.py"
cp "$ROOT_DIR/deployment/verify-release.py" "$ARTIFACT_DIR/verify-release.py"
printf 'Created release artifact: %s\n' "$ARTIFACT_PATH"
