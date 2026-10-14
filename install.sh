#!/bin/sh
# One-line install for a Pi / Linux box / Mac:
#   curl -fsSL https://raw.githubusercontent.com/JoshBong/fuzzyfriends/main/install.sh | sh
# Clones to ~/fuzzyfriends, starts the settings page + checker, and adds an @reboot cron line so it survives restarts.
set -e
DIR="$HOME/fuzzyfriends"
PORT="${FUZZYFRIEND_PORT:-8484}"

command -v python3 >/dev/null || { echo "need python3"; exit 1; }
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull -q; else git clone -q https://github.com/JoshBong/fuzzyfriends "$DIR"; fi

RUN="cd $DIR && python3 -m fuzzyfriend serve --host 0.0.0.0 --port $PORT >> $DIR/fuzzyfriend.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'fuzzyfriend serve'; echo "@reboot $RUN" ) | crontab -

pkill -f 'fuzzyfriend serve' 2>/dev/null || true
nohup sh -c "$RUN" >/dev/null 2>&1 &

IP=$( (hostname -I 2>/dev/null || ipconfig getifaddr en0 2>/dev/null) | awk '{print $1}')
echo "fuzzyfriend running. Edit what you want at http://${IP:-localhost}:$PORT (from any device on your network)"
echo "Update later by re-running this installer."
