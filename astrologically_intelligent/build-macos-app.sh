#!/bin/bash
# Build a downloadable macOS launcher app + .dmg for Astrologically Intelligent.
#
#   ./build-macos-app.sh
#
# Produces:
#   dist/Astrologically Intelligent.app   — double-click: starts the local server (using this
#                         repo's venv) and opens the UI in an app-style window.
#   dist/Astrologically Intelligent.dmg   — drag-to-Applications disk image (the downloadable).
#
# This is a *launcher* wrapper: it drives the venv we set up in this repo, it
# does not bundle Python. The install path is baked into the app at build time,
# so rebuild if you move the repo. Override the port with ASTRO_AI_PORT (legacy ODYSSEUS_PORT is also accepted).
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="Astrologically Intelligent"
APP_EXECUTABLE="AstrologicallyIntelligent"
INSTALL_DIR="$REPO_DIR"
PORT="${ASTRO_AI_PORT:-${ODYSSEUS_PORT:-7860}}"
DIST="$REPO_DIR/dist"
APP="$DIST/$APP_NAME.app"

echo "Building $APP_NAME.app"
echo "  install dir: $INSTALL_DIR"
echo "  port:        $PORT"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# ── Icon (best effort) -- derive the app icon from the installed PWA asset ──
if [ -f "$REPO_DIR/static/icons/icon-512.png" ] && command -v sips >/dev/null 2>&1; then
  TMPIMG="$(mktemp -d)"
  sips -z 512 512 "$REPO_DIR/static/icons/icon-512.png" --out "$TMPIMG/icon.png" >/dev/null 2>&1
  if sips -s format icns "$TMPIMG/icon.png" --out "$APP/Contents/Resources/astrologically-intelligent.icns" >/dev/null 2>&1; then
    echo "  icon:        astrologically-intelligent.icns"
  else
    echo "  icon:        (skipped - conversion failed)"
  fi
  rm -rf "$TMPIMG"
else
  echo "  icon:        (skipped - PWA icon or sips unavailable)"
fi
cp -R "$REPO_DIR/licenses" "$APP/Contents/Resources/licenses"
cp "$REPO_DIR/THIRD_PARTY_PROVENANCE.json" "$REPO_DIR/ACKNOWLEDGMENTS.md" "$APP/Contents/Resources/"

# ── Info.plist ──
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>            <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>     <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>      <string>com.japstudios.astrologicallyintelligent</string>
    <key>CFBundleVersion</key>         <string>1.0</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>CFBundlePackageType</key>     <string>APPL</string>
    <key>CFBundleExecutable</key>      <string>$APP_EXECUTABLE</string>
    <key>CFBundleIconFile</key>        <string>astrologically-intelligent</string>
    <key>LSMinimumSystemVersion</key>  <string>11.0</string>
    <key>NSHighResolutionCapable</key> <true/>
    <key>LSUIElement</key>             <false/>
</dict>
</plist>
PLIST

# ── Launcher executable (placeholders filled below) ──
cat > "$APP/Contents/MacOS/$APP_EXECUTABLE.tmpl" <<'LAUNCHER'
#!/bin/bash
# Astrologically Intelligent.app — start the local server and open the UI in an app window.
INSTALL_DIR="__INSTALL_DIR__"
PORT="__PORT__"
URL="http://127.0.0.1:${PORT}"
# uvicorn is started with --port below, but APP_PORT is what the app itself
# reads when it needs to build a URL for this instance (internal_api_base(),
# companion pairing, the MCP OAuth callback), so export it as well.
export APP_PORT="$PORT"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

UVICORN="$INSTALL_DIR/venv/bin/uvicorn"
LOG="$INSTALL_DIR/logs/astrologically-intelligent-app.log"

notify() { /usr/bin/osascript -e "display notification \"$1\" with title \"Astrologically Intelligent\"" >/dev/null 2>&1; }
die_gui() {
  /usr/bin/osascript -e "display dialog \"$1\" with title \"Astrologically Intelligent\" buttons {\"OK\"} default button 1 with icon stop" >/dev/null 2>&1
  exit 1
}

[ -x "$UVICORN" ] || die_gui "Astrologically Intelligent isn't set up yet. Open Terminal and run:

cd $INSTALL_DIR
python3.11 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python setup.py"

# Open the UI in a chrome-less app window (Chromium browsers), else default browser.
open_ui() {
  local b base exe bin
  for b in "Google Chrome" "Microsoft Edge" "Brave Browser" "Chromium"; do
    for base in "/Applications" "$HOME/Applications"; do
      if [ -d "$base/$b.app" ]; then
        exe="$(/usr/bin/defaults read "$base/$b.app/Contents/Info" CFBundleExecutable 2>/dev/null)"
        bin="$base/$b.app/Contents/MacOS/$exe"
        if [ -x "$bin" ]; then
          "$bin" --app="$URL" --new-window >/dev/null 2>&1 &
          return 0
        fi
      fi
    done
  done
  /usr/bin/open "$URL"
}

mkdir -p "$INSTALL_DIR/logs"

# Already running? Just open the UI.
if /usr/bin/curl -s -o /dev/null --max-time 2 "$URL"; then
  open_ui
  exit 0
fi

notify "Starting…"
cd "$INSTALL_DIR" || die_gui "Install folder not found: $INSTALL_DIR"
if [ "$(uname -m)" = "arm64" ]; then
  arch -arm64 "$UVICORN" app:app --host 127.0.0.1 --port "$PORT" >>"$LOG" 2>&1 &
else
  "$UVICORN" app:app --host 127.0.0.1 --port "$PORT" >>"$LOG" 2>&1 &
fi
SERVER_PID=$!

# Quitting the app stops the server it started.
trap 'kill $SERVER_PID 2>/dev/null; exit 0' TERM INT

# Wait for readiness (first run downloads an embedding model — allow ~2 min).
READY=0
for i in $(seq 1 120); do
  /usr/bin/curl -s -o /dev/null --max-time 2 "$URL" && { READY=1; break; }
  kill -0 "$SERVER_PID" 2>/dev/null || die_gui "Astrologically Intelligent failed to start. Log:
$LOG"
  sleep 1
done

if [ "$READY" = "1" ]; then
  open_ui
else
  notify "Astrologically Intelligent is taking a while — open $URL once it finishes starting."
fi
wait "$SERVER_PID"
LAUNCHER

sed -e "s|__INSTALL_DIR__|$INSTALL_DIR|g" -e "s|__PORT__|$PORT|g" \
    "$APP/Contents/MacOS/$APP_EXECUTABLE.tmpl" > "$APP/Contents/MacOS/$APP_EXECUTABLE"
rm -f "$APP/Contents/MacOS/$APP_EXECUTABLE.tmpl"
chmod +x "$APP/Contents/MacOS/$APP_EXECUTABLE"

# Refresh Finder's icon cache for the new bundle.
touch "$APP"

# ── .dmg (drag-to-Applications) ──
echo "Packaging dist/$APP_NAME.dmg"
STAGE="$(mktemp -d)/dmg"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
rm -f "$DIST/$APP_NAME.dmg"
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGE" -ov -format UDZO "$DIST/$APP_NAME.dmg" >/dev/null
rm -rf "$STAGE"

echo ""
echo "Done:"
echo "  $APP"
echo "  $DIST/$APP_NAME.dmg"
echo ""
echo "Run it:        open '$APP'"
echo "Install:       open '$DIST/$APP_NAME.dmg'  (drag Astrologically Intelligent to Applications)"
