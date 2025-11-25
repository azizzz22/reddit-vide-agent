#!/bin/bash

# Script to launch Chrome with remote debugging
# This allows Playwright to connect to your existing Chrome session

echo "Launching Chrome with Remote Debugging..."
echo "Port: 9222"
echo ""

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/Library/Application Support/Google/Chrome"
