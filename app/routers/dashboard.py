from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["dashboard"])

# Configure templates
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Serve the monitoring dashboard
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/", response_class=HTMLResponse)
async def root_redirect(request: Request):
    """
    Redirect root to dashboard
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})
