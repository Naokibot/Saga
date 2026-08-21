#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=0.50.0
SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1787011200}
export SOURCE_DATE_EPOCH

# Python reference wheel is optional conformance/reference material only.
# Normal Saga Native installers do not embed Python or require it at runtime.
rm -rf "$ROOT/build" "$ROOT/saga_language.egg-info" "$ROOT/dist"
mkdir -p "$ROOT/dist"
if command -v python >/dev/null 2>&1; then
  python -m pip wheel "$ROOT" --no-deps --no-build-isolation -w "$ROOT/dist" || true
fi

cd "$ROOT/implementations/go"
rm -rf bin && mkdir -p bin
for target in linux/amd64 linux/arm64 windows/amd64 windows/arm64 darwin/amd64 darwin/arm64; do
  GOOS=${target%/*}; GOARCH=${target#*/}; ext=
  [ "$GOOS" = windows ] && ext=.exe
  CGO_ENABLED=0 GOOS=$GOOS GOARCH=$GOARCH go build -trimpath -ldflags='-s -w -buildid=' \
    -o "bin/saga-native-$GOOS-$GOARCH$ext" ./cmd/saga-go
  CGO_ENABLED=0 GOOS=$GOOS GOARCH=$GOARCH go build -tags sagaruntime -trimpath -ldflags='-s -w -buildid=' \
    -o "bin/saga-runtime-$GOOS-$GOARCH$ext" ./cmd/saga-go
done

PAYLOAD="$ROOT/installer-native/cmd/saga-installer/payload"
rm -rf "$PAYLOAD" && mkdir -p "$PAYLOAD"
cp "$ROOT/implementations/go/bin/"saga-native-* "$PAYLOAD/"
cp "$ROOT/implementations/go/bin/"saga-runtime-* "$PAYLOAD/"
cp "$ROOT/selfhost/sagac.saga" "$PAYLOAD/sagac.saga"

cd "$ROOT/installer-native"
rm -rf bin && mkdir -p bin
for target in linux/amd64 linux/arm64 windows/amd64 windows/arm64; do
  GOOS=${target%/*}; GOARCH=${target#*/}; ext=
  [ "$GOOS" = windows ] && ext=.exe
  CGO_ENABLED=0 GOOS=$GOOS GOARCH=$GOARCH go build -tags saga_installer_payload -trimpath -ldflags="-s -w -buildid= -X main.version=$VERSION" \
    -o "bin/saga-installer-$GOOS-$GOARCH-$VERSION$ext" ./cmd/saga-installer
done
