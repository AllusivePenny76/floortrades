"""FloorTrades — self-hosted congressional trading tracker."""
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.background import BackgroundScheduler

from . import config, db, ingest, queries

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("floortrades")

scheduler = BackgroundScheduler(daemon=True)
_refresh_lock = threading.Lock()


def _safe_refresh(force=False):
    """Run a refresh guarded by a lock so manual + scheduled never overlap."""
    if not _refresh_lock.acquire(blocking=False):
        log.info("Refresh already in progress; skipping")
        return None
    try:
        return ingest.refresh(force=force)
    except Exception:
        log.exception("Refresh failed")
        return None
    finally:
        _refresh_lock.release()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    if config.REFRESH_ON_START and ingest.needs_refresh(config.REFRESH_HOURS):
        threading.Thread(target=_safe_refresh, daemon=True).start()
    scheduler.add_job(
        _safe_refresh, "interval", hours=config.REFRESH_HOURS,
        id="refresh", replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# ---- template helpers -------------------------------------------------------

def fmt_money(v):
    if v is None:
        return "—"
    v = float(v)
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"


def fmt_pct(v):
    if v is None:
        return "—"
    return f"{v:+.1f}%"


def party_class(p):
    return {"D": "dem", "R": "rep", "I": "ind"}.get(p, "other")


templates.env.filters["money"] = fmt_money
templates.env.filters["pct"] = fmt_pct
templates.env.filters["party_class"] = party_class


def base_ctx(request):
    return {
        "request": request,
        "app_name": config.APP_NAME,
        "version": config.APP_VERSION,
        "last_refresh": db.get_meta("last_refresh"),
        "attribution": db.get_meta("attribution", ""),
        "stats": queries.overview_stats(),
    }


# ---- pages ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request, chamber: str = "", party: str = "",
         order: str = "weighted_excess"):
    ctx = base_ctx(request)
    ctx.update(
        rows=queries.leaderboard(chamber=chamber or None, party=party or None, order=order),
        chamber=chamber, party=party, order=order,
        active="leaderboard",
    )
    return templates.TemplateResponse("leaderboard.html", ctx)


@app.get("/trades", response_class=HTMLResponse)
def trades(request: Request, view: str = "top", chamber: str = "",
           txn: str = "", late: int = 0, days: int = 0):
    ctx = base_ctx(request)
    if view == "recent":
        rows = queries.recent_trades(chamber=chamber or None)
    else:
        rows = queries.top_trades(
            chamber=chamber or None, txn_type=txn or None,
            late_only=bool(late), days=days or None,
        )
    ctx.update(rows=rows, view=view, chamber=chamber, txn=txn, late=late,
               days=days, active="trades",
               top_tickers=queries.top_tickers())
    return templates.TemplateResponse("trades.html", ctx)


@app.get("/politician/{filer_id}", response_class=HTMLResponse)
def politician(request: Request, filer_id: str):
    data = queries.politician(filer_id)
    if not data["filer"] and not data["trades"]:
        return templates.TemplateResponse("not_found.html", base_ctx(request), status_code=404)
    ctx = base_ctx(request)
    ctx.update(active="leaderboard", **data)
    return templates.TemplateResponse("politician.html", ctx)


@app.get("/ticker/{symbol}", response_class=HTMLResponse)
def ticker(request: Request, symbol: str):
    data = queries.ticker(symbol)
    ctx = base_ctx(request)
    ctx.update(active="trades", **data)
    return templates.TemplateResponse("ticker.html", ctx)


@app.get("/search", response_class=HTMLResponse)
def search(request: Request, q: str = ""):
    ctx = base_ctx(request)
    ctx.update(q=q, results=queries.search(q) if q.strip() else None, active="")
    return templates.TemplateResponse("search.html", ctx)


# ---- actions & API ----------------------------------------------------------

@app.post("/refresh")
def refresh_now():
    started = threading.Thread(target=_safe_refresh, kwargs={"force": True}, daemon=True)
    started.start()
    return RedirectResponse("/", status_code=303)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "trades": db.count_rows("trades"),
            "last_refresh": db.get_meta("last_refresh")}


@app.get("/api/leaderboard")
def api_leaderboard(chamber: str = Query(""), party: str = Query(""),
                    order: str = Query("weighted_excess"), limit: int = 100):
    return JSONResponse(queries.leaderboard(
        chamber=chamber or None, party=party or None, order=order, limit=limit))


@app.get("/api/trades")
def api_trades(limit: int = 100, chamber: str = "", txn: str = "", late: int = 0):
    return JSONResponse(queries.top_trades(
        chamber=chamber or None, txn_type=txn or None, late_only=bool(late), limit=limit))
