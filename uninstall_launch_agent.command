#!/bin/zsh
set -euo pipefail

LABEL="com.vitalii.blink.watcher"
TARGET_PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl unload "$TARGET_PLIST" >/dev/null 2>&1 || true
rm -f "$TARGET_PLIST"

echo "Blink Watcher LaunchAgent unloaded and removed."

APP_LABEL="com.vitalii.blink.app"
APP_TARGET_PLIST="$HOME/Library/LaunchAgents/$APP_LABEL.plist"
launchctl unload "$APP_TARGET_PLIST" >/dev/null 2>&1 || true
rm -f "$APP_TARGET_PLIST"
echo "Blink.app LaunchAgent unloaded and removed."
