#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/vitaliiprotsiuk/Desktop/Blink"
LABEL="com.vitalii.blink.watcher"
SOURCE_PLIST="$PROJECT_DIR/launchd/$LABEL.plist"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/$LABEL.plist"

mkdir -p "$TARGET_DIR"
cp "$SOURCE_PLIST" "$TARGET_PLIST"
launchctl unload "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl load "$TARGET_PLIST"
launchctl start "$LABEL" >/dev/null 2>&1 || true

APP_LABEL="com.vitalii.blink.app"
APP_SOURCE_PLIST="$PROJECT_DIR/launchd/$APP_LABEL.plist"
APP_TARGET_PLIST="$TARGET_DIR/$APP_LABEL.plist"
cp "$APP_SOURCE_PLIST" "$APP_TARGET_PLIST"
launchctl unload "$APP_TARGET_PLIST" >/dev/null 2>&1 || true
launchctl load "$APP_TARGET_PLIST"
launchctl start "$APP_LABEL" >/dev/null 2>&1 || true

echo "Blink watcher and Blink.app LaunchAgents installed and started."
echo "Status: $PROJECT_DIR/status_watcher.command"
