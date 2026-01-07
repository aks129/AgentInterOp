from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os

router = APIRouter()

# Feature flags
UI_EXPERIMENTAL = os.getenv("UI_EXPERIMENTAL", "false").lower() == "true"

# Setup templates
templates = None
try:
    base = Path(__file__).resolve().parent.parent
    templates_dir = base / "web" / "templates"
    if templates_dir.exists():
        templates = Jinja2Templates(directory=str(templates_dir))
    else:
        print(f"[WARN] no templates dir: {templates_dir}")
except Exception as e:
    print(f"[WARN] templates setup skipped: {e}")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """GET / renders comprehensive splash page as default interface"""
    if templates:
        return templates.TemplateResponse("splash.html", {
            "request": request
        })
    else:
        return HTMLResponse("<h1>AgentInterOp</h1><p>Healthcare Agent Interoperability Platform</p>")

@router.get("/banterop", response_class=HTMLResponse)
async def banterop_ui(request: Request):
    """GET /banterop renders Agent 2 Agent Chat UI"""
    base = Path(__file__).resolve().parent.parent
    banterop_dir = base / "web" / "experimental" / "banterop"

    if (banterop_dir / "index.html").exists():
        with open(banterop_dir / "index.html", 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content)
    else:
        # Fallback to splash if Agent 2 Agent Chat not available
        if templates:
            return templates.TemplateResponse("splash.html", {
                "request": request
            })
        else:
            return HTMLResponse("<h1>Agent 2 Agent Chat</h1><p>Not available in this environment</p>")

@router.get("/legacy", response_class=HTMLResponse)
async def legacy_ui(request: Request):
    """GET /legacy renders legacy index.html interface"""
    if templates:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "UI_EXPERIMENTAL": UI_EXPERIMENTAL
        })
    else:
        return HTMLResponse("<h1>Multi-Agent Demo</h1><p>Templates not available in this environment</p>")

@router.get("/agents", response_class=HTMLResponse)
async def agent_management_ui(request: Request):
    """GET /agents renders the Agent Management UI"""
    if templates:
        return templates.TemplateResponse("agent_management.html", {
            "request": request
        })
    else:
        return HTMLResponse("<h1>Agent Management</h1><p>Templates not available in this environment</p>")

@router.get("/studio", response_class=HTMLResponse)
async def agent_studio_ui(request: Request):
    """GET /studio renders the comprehensive Agent Studio UI"""
    if templates:
        return templates.TemplateResponse("agent_studio.html", {
            "request": request
        })
    else:
        return HTMLResponse("<h1>Agent Studio</h1><p>Templates not available in this environment</p>")

@router.get("/use-cases", response_class=HTMLResponse)
async def use_cases_ui(request: Request):
    """GET /use-cases renders the Healthcare AI Agent Use Cases page"""
    if templates:
        return templates.TemplateResponse("use_cases.html", {
            "request": request
        })
    else:
        return HTMLResponse("<h1>Healthcare AI Agent Use Cases</h1><p>Templates not available in this environment</p>")

@router.get("/docs/{doc_name}", response_class=HTMLResponse)
async def documentation_page(doc_name: str, request: Request):
    """Serve markdown documentation as HTML - redirects to GitHub for serverless compatibility"""

    # Map documentation to GitHub URLs
    github_docs = {
        "AGENT_STUDIO.md": "https://github.com/aks129/AgentInterOp/blob/main/docs/AGENT_STUDIO.md",
        "AGENT_MANAGEMENT.md": "https://github.com/aks129/AgentInterOp/blob/main/docs/AGENT_MANAGEMENT.md"
    }

    if doc_name not in github_docs:
        return HTMLResponse("""
        <html>
        <head><title>Documentation Not Found</title></head>
        <body style="font-family: sans-serif; padding: 40px; max-width: 800px; margin: 0 auto;">
            <h1>Documentation Not Found</h1>
            <p>Available documentation:</p>
            <ul>
                <li><a href="/docs/AGENT_STUDIO.md">Agent Studio Documentation</a></li>
                <li><a href="/docs/AGENT_MANAGEMENT.md">Agent Management Guide</a></li>
            </ul>
            <p><a href="/">← Back to Home</a></p>
        </body>
        </html>
        """, status_code=404)

    github_url = github_docs[doc_name]

    # Return a nice redirect page
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="0; url={github_url}">
        <title>Redirecting to Documentation...</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }}
            .container {{
                text-align: center;
                padding: 40px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                backdrop-filter: blur(10px);
                max-width: 600px;
            }}
            h1 {{
                font-size: 32px;
                margin-bottom: 20px;
            }}
            p {{
                font-size: 18px;
                margin-bottom: 30px;
                opacity: 0.9;
            }}
            .spinner {{
                border: 4px solid rgba(255, 255, 255, 0.3);
                border-top: 4px solid white;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            a {{
                color: white;
                text-decoration: underline;
                font-weight: 600;
            }}
            a:hover {{
                opacity: 0.8;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📚 Redirecting to Documentation</h1>
            <div class="spinner"></div>
            <p>You're being redirected to the documentation on GitHub...</p>
            <p style="font-size: 14px;">If you're not redirected automatically, <a href="{github_url}">click here</a>.</p>
            <p style="font-size: 14px; margin-top: 30px;"><a href="/">← Back to Home</a></p>
        </div>
    </body>
    </html>
    """)

@router.get("/experimental/banterop", response_class=HTMLResponse)
async def experimental_banterop(request: Request):
    """GET /experimental/banterop renders Agent 2 Agent Chat scenario UI"""
    base = Path(__file__).resolve().parent.parent
    banterop_dir = base / "web" / "experimental" / "banterop"

    if (banterop_dir / "index.html").exists():
        with open(banterop_dir / "index.html", 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content)
    else:
        return HTMLResponse("<h1>Agent 2 Agent Chat</h1><p>Frontend files not found</p>")

@router.get("/experimental/banterop/banterop.js")
async def experimental_banterop_js():
    """Serve banterop.js file"""
    base = Path(__file__).resolve().parent.parent
    js_file = base / "web" / "experimental" / "banterop" / "banterop.js"

    if js_file.exists():
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, media_type="application/javascript")
    else:
        return Response("// banterop.js not found", media_type="application/javascript")

@router.get("/banterop.js")
async def banterop_js():
    """Serve banterop.js file from root for default UI"""
    base = Path(__file__).resolve().parent.parent
    js_file = base / "web" / "experimental" / "banterop" / "banterop.js"

    if js_file.exists():
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, media_type="application/javascript")
    else:
        return Response("// banterop.js not found", media_type="application/javascript")

@router.get("/debug", response_class=HTMLResponse)
async def debug_console(request: Request):
    """Debug console for troubleshooting Agent 2 Agent Chat configuration"""
    base = Path(__file__).resolve().parent.parent
    debug_file = base / "web" / "debug.html"

    if debug_file.exists():
        with open(debug_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content)
    else:
        return HTMLResponse("<h1>Debug Console</h1><p>Debug page not found</p>")

@router.get("/partner_connect", response_class=HTMLResponse)
async def partner_connect(request: Request):
    """Partner Connect UI"""
    if templates:
        return templates.TemplateResponse("partner_connect.html", {"request": request})
    else:
        return HTMLResponse("<h1>Partner Connect</h1><p>Templates not available in this environment</p>")

@router.get("/test_harness", response_class=HTMLResponse)
async def test_harness(request: Request):
    """Test Harness UI"""
    if templates:
        return templates.TemplateResponse("test_harness.html", {"request": request})
    else:
        return HTMLResponse("<h1>Test Harness</h1><p>Templates not available in this environment</p>")
