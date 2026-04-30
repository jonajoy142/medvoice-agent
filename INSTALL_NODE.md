# Node.js Installation Required

The frontend requires Node.js 18+ to run. Here are the installation options:

## Option 1: Install Node.js (Recommended)

### macOS using Homebrew:
```bash
brew install node
```

### macOS using installer:
1. Download from https://nodejs.org/
2. Install the LTS version (18.x or 20.x)

### Verify installation:
```bash
node --version
npm --version
```

## Option 2: Use Backend Only (Quick Test)

If you want to test the system without the frontend:

1. Start the backend:
```bash
./start_backend.sh
```

2. Test with API calls:
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Test voice endpoint (will require audio file)
curl -X POST http://localhost:8000/api/v1/voice \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "voice_type": "female"}'
```

## Option 3: Use Python Simple Server (Temporary)

Create a simple HTML interface to test the backend:

```bash
cd frontend
python3 -m http.server 3000
```

Then access http://localhost:3000 in your browser.

## After Node.js Installation

Once Node.js is installed:

1. Install frontend dependencies:
```bash
cd frontend
npm install
```

2. Start the frontend:
```bash
npm run dev
```

3. Access the full application at http://localhost:3000

## Troubleshooting

- If you get permission errors, try with `sudo`
- If brew is not installed, install it first: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
- On macOS, you may need to restart your terminal after Node.js installation
