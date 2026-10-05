#!/bin/bash
# MirkoMagic launcher: finds Python 3.9+ and runs the local app server in the
# foreground, so macOS keeps it alive as the app process (a backgrounded child
# gets killed when the app's main executable exits). The server opens the browser.
RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
SUPPORT="$HOME/Library/Application Support/MirkoMagic"
mkdir -p "$SUPPORT"

PY=""
for p in /opt/homebrew/bin/python3 /usr/local/bin/python3 \
         /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /usr/bin/python3; do
  if [ -x "$p" ] && "$p" -c 'import sys, venv; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
    PY="$p"; break
  fi
done

if [ -z "$PY" ]; then
  answer=$(osascript -e 'display dialog "MirkoMagic braucht einmalig Python 3 (kostenlos, ca. 2 Minuten).\n\nNach der Installation die App einfach erneut öffnen." buttons {"Abbrechen", "Python herunterladen"} default button "Python herunterladen" with title "MirkoMagic"' -e 'button returned of result' 2>/dev/null)
  [ "$answer" = "Python herunterladen" ] && open "https://www.python.org/downloads/macos/"
  exit 0
fi

LOG="$SUPPORT/server.log"
"$PY" "$RES/server.py" >"$LOG" 2>&1
if [ $? -ne 0 ]; then
  answer=$(osascript -e 'display dialog "MirkoMagic wurde mit einem Fehler beendet.\n\nBitte die Protokolldatei an Claude schicken." buttons {"Schließen", "Protokoll zeigen"} default button "Protokoll zeigen" with title "MirkoMagic"' -e 'button returned of result' 2>/dev/null)
  [ "$answer" = "Protokoll zeigen" ] && open -R "$LOG"
fi
exit 0
