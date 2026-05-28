#!/bin/bash

echo "Starting MedVoice AI Frontend..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Please install Node.js 18+"
    exit 1
fi

cd "$(dirname "$0")"

# Install dependencies if not already installed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start the development server
echo "Starting React development server on http://localhost:3000"
npm run dev
