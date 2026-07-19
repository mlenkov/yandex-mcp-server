from datetime import datetime, timedelta, timezone

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.config import settings
from app.crypto import crypto
from app.database import async_session_factory
from app.models import MCPUser, MCPYandexAccount, ServiceType

SERVICE_SCOPES = {
    ServiceType.direct: "direct:campaigns direct:reports direct:ads",
    ServiceType.metrika: "metrika:read",
    ServiceType.webmaster: "webmaster:read",
    ServiceType.audience: "audience:read",
    ServiceType.admetrica: "admetrica:read",
}

SERVICE_LABELS = {
    ServiceType.direct: "Яндекс.Директ",
    ServiceType.metrika: "Яндекс.Метрика",
    ServiceType.webmaster: "Яндекс.Вебмастер",
    ServiceType.audience: "Яндекс.Аудитории",
    ServiceType.admetrica: "Яндекс.AdMetrica",
}

app = FastAPI(title="Yandex MCP Admin")

templates = Jinja2Templates(directory="admin/templates")
app.mount("/admin/static", StaticFiles(directory="admin/static"), name="static")


def _user_email(request: Request) -> str:
    return request.headers.get("X-Forwarded-User") or request.headers.get("X-Forwarded-Email") or "unknown"


async def _get_or_create_user(email: str) -> MCPUser:
    async with async_session_factory() as session:
        result = await session.execute(select(MCPUser).where(MCPUser.external_id == email))
        user = result.scalar_one_or_none()
        if user is None:
            user = MCPUser(external_id=email)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


def _token_status(expires_at: datetime | None) -> str:
    if expires_at is None:
        return "unknown"
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        return "expired"
    if expires_at < now + timedelta(days=7):
        return "expiring_soon"
    return "valid"


@app.get("/admin/", response_class=HTMLResponse)
async def dashboard(request: Request):
    email = _user_email(request)
    user = await _get_or_create_user(email)
    async with async_session_factory() as session:
        result = await session.execute(
            select(MCPYandexAccount).where(MCPYandexAccount.user_id == user.id)
        )
        integrations = result.scalars().all()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_email": email,
        "integrations": integrations,
        "token_status": _token_status,
        "service_labels": SERVICE_LABELS,
    })


@app.get("/admin/integrations", response_class=HTMLResponse)
async def integrations_list(request: Request):
    email = _user_email(request)
    user = await _get_or_create_user(email)
    async with async_session_factory() as session:
        result = await session.execute(
            select(MCPYandexAccount).where(MCPYandexAccount.user_id == user.id)
        )
        integrations = result.scalars().all()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_email": email,
        "integrations": integrations,
        "token_status": _token_status,
        "service_labels": SERVICE_LABELS,
    })


@app.get("/admin/integrations/add", response_class=HTMLResponse)
async def add_integration_page(request: Request):
    return templates.TemplateResponse("add_integration.html", {
        "request": request,
        "services": [
            {"type": st.value, "label": SERVICE_LABELS[st]}
            for st in ServiceType
        ],
    })


@app.get("/admin/oauth/start")
async def oauth_start(service: str, request: Request):
    service_type = ServiceType(service)
    scope = SERVICE_SCOPES[service_type]
    state = crypto.fernet.encrypt(f"{service}:{_user_email(request)}".encode()).decode()
    oauth_url = (
        f"https://oauth.yandex.ru/authorize?"
        f"response_type=code&"
        f"client_id={settings.yandex_client_id}&"
        f"redirect_uri=https://app.mais.agency/admin/oauth/callback&"
        f"scope={scope}&"
        f"state={state}&"
        f"force_confirm=yes"
    )
    resp = RedirectResponse(oauth_url)
    resp.set_cookie("oauth_state", state, max_age=600, httponly=True, secure=True, samesite="lax")
    return resp


@app.get("/admin/oauth/callback")
async def oauth_callback(code: str = Query(...), state: str = Query(...), request: Request = None):
    user_email = _user_email(request)
    state_cookie = request.cookies.get("oauth_state", "")
    if not state_cookie or state_cookie != state:
        return HTMLResponse("Invalid state (CSRF)", status_code=403)
    try:
        decrypted = crypto.fernet.decrypt(state.encode()).decode()
        service_str, _ = decrypted.split(":", 1)
    except Exception:
        return HTMLResponse("Invalid state", status_code=403)
    service_type = ServiceType(service_str)
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://oauth.yandex.ru/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.yandex_client_id,
            "client_secret": settings.yandex_client_secret,
        })
        resp.raise_for_status()
        token_data = resp.json()
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://login.yandex.ru/info",
            headers={"Authorization": f"OAuth {access_token}"},
        )
        user_resp.raise_for_status()
        yandex_user = user_resp.json()
    account_name = yandex_user.get("display_name", yandex_user.get("login", f"Yandex {service_str}"))
    user = await _get_or_create_user(user_email)
    async with async_session_factory() as session:
        account = MCPYandexAccount(
            user_id=user.id,
            account_name=account_name,
            service_type=service_type,
            encrypted_access_token=crypto.encrypt(access_token),
            encrypted_refresh_token=crypto.encrypt(refresh_token) if refresh_token else None,
            token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            is_active=True,
        )
        session.add(account)
        await session.commit()
    resp = RedirectResponse("/admin/")
    resp.delete_cookie("oauth_state")
    return resp


@app.post("/admin/integrations/{account_id}/delete")
async def delete_integration(account_id: int, request: Request):
    user_email = _user_email(request)
    user = await _get_or_create_user(user_email)
    async with async_session_factory() as session:
        result = await session.execute(
            select(MCPYandexAccount).where(
                MCPYandexAccount.id == account_id,
                MCPYandexAccount.user_id == user.id,
            )
        )
        account = result.scalar_one_or_none()
        if account:
            account.is_active = False
            await session.commit()
    return RedirectResponse("/admin/")


@app.get("/admin/ping")
async def ping():
    return {"status": "ok", "service": "yandex-admin"}
