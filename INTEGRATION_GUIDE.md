# React UI Integration Guide

## Step 1: Build Your React App
In your bolt.new React project:
```bash
npm run build
```

## Step 2: Copy Build Files
Copy the contents of your React `build/` or `dist/` folder to replace `app/web/`:

```bash
# Remove old web files (backup already created)
rm -rf app/web/static/*
rm -rf app/web/templates/*

# Copy your React build files
cp -r /path/to/your/react/build/* app/web/static/
```

## Step 3: Update Flask Routes
The main.py file needs to serve your React app instead of templates.

## Step 4: Configure API Base URL
In your React app, set the API base URL to:
- Development: `http://localhost:5000`
- Production: Your deployed backend URL

## Step 5: Test Integration
1. Start the backend: `python main.py` or `gunicorn main:app`
2. Your React app should now be served at `http://localhost:5000`
3. All API calls should work through the same origin

## API Endpoints Your React App Can Use:
- GET/POST `/api/protocol` - Protocol switching
- GET/POST `/api/config` - Configuration management
- GET/POST `/api/scenarios/*` - Scenario management
- GET/POST `/api/fhir/*` - FHIR integration
- POST `/api/bridge/demo/a2a` - A2A streaming
- POST `/api/mcp/*` - MCP tools
- GET `/api/trace/*` - Decision traces
- GET/POST `/api/room/*` - Export/import
- POST `/api/scenarios/narrative` - AI processing

## Environment Variables Needed:
- `ANTHROPIC_API_KEY` - For AI narrative processing
- `SESSION_SECRET` - For session security (optional)