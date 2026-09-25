#!/bin/bash
echo "🎙️  Starting MedVoice Demo..."
echo ""

# Kill any existing instance
pkill -f "node demo-server.js" 2>/dev/null
sleep 0.5

# Start the server
node demo-server.js &
sleep 1.5

# Open in Chrome
open -a "Google Chrome" http://localhost:3333 2>/dev/null || open http://localhost:3333

echo "Demo running at http://localhost:3333"
wait
