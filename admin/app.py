import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.config import settings
from app.crypto import crypto
from app.database import async_session_factory
from app.models import MCPUser, MCPYandexAccount, ServiceType

logger = logging.getLogger("yandex-admin")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

SERVICE_SCOPES = {
    ServiceType.direct: "direct:api",
    ServiceType.metrika: "metrika:read",
    ServiceType.webmaster: "webmaster:api",
    ServiceType.audience: "audience:api",
    ServiceType.admetrica: "admetrica:api",
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
    return request.headers.get("X-Forwarded-Email") or request.headers.get("X-Forwarded-User") or "unknown"


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


async def _fetch_available_accounts(service_type: ServiceType, access_token: str) -> list[dict]:
    """Получить список доступных аккаунтов через API Яндекса после OAuth."""
    async with httpx.AsyncClient() as client:
        if service_type == ServiceType.direct:
            resp = await client.post(
                "https://api.direct.yandex.com/json/v5/clients",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={"method": "get", "params": {"SelectionCriteria": {}, "FieldNames": ["Login"]}},
                timeout=10,
            )
            if resp.status_code == 200:
                clients = resp.json().get("result", {}).get("Clients", [])
                if clients:
                    account_name = clients[0].get("Login", "Direct Account")
                else:
                    account_name = "Direct Account"
                return [{"login": account_name, "type": "CLIENT", "source": "Текущий аккаунт"}]

        elif service_type == ServiceType.metrika:
            resp = await client.get(
                "https://api-metrika.yandex.net/management/v1/counters",
                headers={"Authorization": f"OAuth {access_token}"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {"id": c.get("id"), "name": c.get("name"), "site": c.get("site")}
                    for c in data.get("counters", [])
                ]

        return []


async def _check_account_status(account: MCPYandexAccount) -> dict:
    """Проверить реальный статус аккаунта через тестовый запрос к API."""
    status = {
        "valid": False,
        "message": "Неизвестно",
        "color": "gray",
        "goals_configured": False,
    }

    if account.token_expires_at:
        if account.token_expires_at < datetime.now(timezone.utc):
            status["message"] = "Токен истёк"
            status["color"] = "red"
            return status
        elif account.token_expires_at < datetime.now(timezone.utc) + timedelta(days=7):
            status["message"] = "Токен истекает скоро"
            status["color"] = "orange"

    if not account.encrypted_access_token:
        status["message"] = "Нет токена"
        status["color"] = "red"
        return status

    try:
        token = crypto.decrypt(account.encrypted_access_token)
        async with httpx.AsyncClient() as client:
            if account.service_type == ServiceType.direct:
                resp = await client.post(
                    "https://api.direct.yandex.com/json/v5/clients",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept-Language": "ru",
                        "Content-Type": "application/json; charset=utf-8",
                    },
                    json={
                        "method": "get",
                        "params": {"SelectionCriteria": {}, "FieldNames": ["Login"]},
                    },
                    timeout=5.0,
                )
            elif account.service_type == ServiceType.metrika:
                resp = await client.get(
                    "https://api-metrika.yandex.net/management/v1/counters",
                    headers={"Authorization": f"OAuth {token}"},
                    timeout=5.0,
                )
            elif account.service_type == ServiceType.webmaster:
                resp = await client.get(
                    "https://api.webmaster.yandex.net/v4/user/",
                    headers={"Authorization": f"OAuth {token}"},
                    timeout=5.0,
                )
            elif account.service_type == ServiceType.audience:
                resp = await client.post(
                    "https://audience-api.ads.yandex.net/management/v1/segments",
                    headers={
                        "Authorization": f"OAuth {token}",
                        "Content-Type": "application/json",
                    },
                    json={"method": "get", "params": {"SelectionCriteria": {}}},
                    timeout=5.0,
                )
            elif account.service_type == ServiceType.admetrica:
                resp = await client.get(
                    "https://api-metrika.yandex.net/management/v1/partners",
                    headers={"Authorization": f"OAuth {token}"},
                    timeout=5.0,
                )
            else:
                resp = None

            if resp and resp.status_code == 200:
                status["valid"] = True
                status["message"] = "Работает"
                status["color"] = "green"
            elif resp and resp.status_code == 401:
                status["message"] = "Токен недействителен"
                status["color"] = "red"
            elif resp and resp.status_code == 403:
                status["message"] = "Нет доступа к API"
                status["color"] = "red"
            else:
                status["message"] = f"Ошибка API ({resp.status_code if resp else 'N/A'})"
                status["color"] = "orange"
    except httpx.TimeoutException:
        status["message"] = "Timeout (сервер не отвечает)"
        status["color"] = "orange"
    except Exception as e:
        status["message"] = f"Ошибка: {str(e)[:50]}"
        status["color"] = "red"

    return status


@app.get("/admin/", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        email = _user_email(request)
        logger.info(f"Dashboard requested by {email}")
        return templates.TemplateResponse(request, "dashboard.html", {
            "user_email": email,
            "service_labels": SERVICE_LABELS,
            "service_types": list(ServiceType),
        })
    except Exception as e:
        logger.exception(f"Dashboard error: {e}")
        return HTMLResponse(f"<h1>Dashboard Error</h1><pre>{e}</pre>", status_code=500)


@app.get("/admin/integrations/{service}", response_class=HTMLResponse)
async def service_page(service: str, request: Request):
    try:
        service_type = ServiceType(service)
    except ValueError:
        return RedirectResponse("/admin/")
    email = _user_email(request)
    user = await _get_or_create_user(email)
    async with async_session_factory() as session:
        result = await session.execute(
            select(MCPYandexAccount).where(
                MCPYandexAccount.user_id == user.id,
                MCPYandexAccount.service_type == service_type,
                MCPYandexAccount.is_active == True,
            )
        )
        integrations = result.scalars().all()

    account_statuses = {}
    for acc in integrations:
        account_statuses[acc.id] = await _check_account_status(acc)

    client_id, _ = settings.get_oauth_credentials(service_type)
    return templates.TemplateResponse(request, "service_page.html", {
        "user_email": email,
        "service": service,
        "service_label": SERVICE_LABELS[service_type],
        "integrations": integrations,
        "account_statuses": account_statuses,
        "client_id": client_id,
    })


@app.get("/admin/oauth/start")
async def oauth_start(service: str, request: Request):
    try:
        service_type = ServiceType(service)
    except ValueError:
        return RedirectResponse("/admin/")

    client_id, client_secret = settings.get_oauth_credentials(service_type)
    if not client_id:
        return HTMLResponse(
            f"<h1>Ошибка конфигурации</h1>"
            f"<p>YANDEX_{service.upper()}_CLIENT_ID не задан в .env.prod</p>",
            status_code=500,
        )

    scope = SERVICE_SCOPES[service_type]
    state = crypto.encrypt(f"{service}:{_user_email(request)}")
    redirect_uri = settings.yandex_redirect_uri or "https://app.mais.agency/admin/oauth/callback"

    oauth_url = (
        f"https://oauth.yandex.com/authorize?"
        f"response_type=code&"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope={scope}&"
        f"state={state}&"
        f"force_confirm=yes"
    )

    resp = RedirectResponse(oauth_url)
    resp.set_cookie("oauth_state", state, max_age=600, httponly=True, secure=True, samesite="lax")
    return resp


@app.get("/admin/oauth/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    if error:
        logger.warning(f"OAuth error: {error} — {error_description}")
        client_id = ""
        if state:
            try:
                decrypted = crypto.decrypt(state)
                service_str, _ = decrypted.split(":", 1)
                cid, _ = settings.get_oauth_credentials(ServiceType(service_str))
                client_id = cid
            except Exception:
                pass
        return templates.TemplateResponse(request, "oauth_error.html", {
            "user_email": _user_email(request),
            "error": error,
            "error_description": error_description or "Unknown error",
            "client_id": client_id,
            "setup_instructions": True,
        })

    if not code or not state:
        return HTMLResponse("Missing code or state parameter", status_code=400)

    user_email = _user_email(request)
    state_cookie = request.cookies.get("oauth_state", "")
    if not state_cookie or state_cookie != state:
        return HTMLResponse("Invalid state (CSRF)", status_code=403)
    try:
        decrypted = crypto.decrypt(state)
        service_str, _ = decrypted.split(":", 1)
    except Exception:
        return HTMLResponse("Invalid state", status_code=403)

    service_type = ServiceType(service_str)

    client_id, client_secret = settings.get_oauth_credentials(service_type)
    redirect_uri = settings.yandex_redirect_uri or "https://app.mais.agency/admin/oauth/callback"
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://oauth.yandex.com/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
        })
        resp.raise_for_status()
        token_data = resp.json()

    access_token = token_data["access_token"]

    accounts = await _fetch_available_accounts(service_type, access_token)

    temp_data = {
        "access_token": access_token,
        "refresh_token": token_data.get("refresh_token"),
        "expires_in": token_data.get("expires_in", 3600),
        "accounts": accounts,
        "service": service_str,
    }

    encrypted = crypto.encrypt(json.dumps(temp_data))
    resp = RedirectResponse("/admin/oauth/select-accounts")
    resp.delete_cookie("oauth_state")
    resp.set_cookie("oauth_temp", encrypted, max_age=300, httponly=True, secure=True, samesite="lax")
    return resp


@app.get("/admin/oauth/select-accounts", response_class=HTMLResponse)
async def select_accounts_page(request: Request):
    temp_cookie = request.cookies.get("oauth_temp")
    if not temp_cookie:
        return RedirectResponse("/admin/")

    try:
        decrypted = crypto.decrypt(temp_cookie)
        temp_data = json.loads(decrypted)
    except Exception:
        return RedirectResponse("/admin/")

    return templates.TemplateResponse(request, "select_accounts.html", {
        "user_email": _user_email(request),
        "service": temp_data["service"],
        "service_label": SERVICE_LABELS[ServiceType(temp_data["service"])],
        "accounts": temp_data["accounts"],
    })


@app.post("/admin/oauth/save-accounts")
async def save_accounts(
    request: Request,
    selected_accounts: list[str] = Form([]),
):
    temp_cookie = request.cookies.get("oauth_temp")
    if not temp_cookie:
        return RedirectResponse("/admin/")

    try:
        decrypted = crypto.decrypt(temp_cookie)
        temp_data = json.loads(decrypted)
    except Exception:
        return RedirectResponse("/admin/")

    user_email = _user_email(request)
    user = await _get_or_create_user(user_email)
    service_type = ServiceType(temp_data["service"])

    access_token = temp_data["access_token"]
    refresh_token = temp_data.get("refresh_token")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=temp_data.get("expires_in", 3600))

    for login in selected_accounts:
        async with async_session_factory() as session:
            account = MCPYandexAccount(
                user_id=user.id,
                account_name=login,
                service_type=service_type,
                encrypted_access_token=crypto.encrypt(access_token),
                encrypted_refresh_token=crypto.encrypt(refresh_token) if refresh_token else None,
                token_expires_at=expires_at,
                is_active=True,
            )
            session.add(account)
            await session.commit()

    resp = RedirectResponse(f"/admin/integrations/{temp_data['service']}", status_code=303)
    resp.delete_cookie("oauth_temp")
    return resp


@app.post("/admin/integrations/{service}/add")
async def add_manual_integration(
    service: str,
    request: Request,
    account_name: str = Form(""),
    login: str = Form(...),
    oauth_token: str = Form(...),
    shared_account_id: Optional[int] = Form(None),
    context: str = Form(""),
    goal_ids: list[str] = Form([]),
    goal_names: list[str] = Form([]),
):
    service_type = ServiceType(service)
    user_email = _user_email(request)
    user = await _get_or_create_user(user_email)

    async with httpx.AsyncClient() as client:
        validate_resp = await client.post(
            "https://api.direct.yandex.com/json/v5/campaigns",
            json={"method": "get", "params": {"SelectionCriteria": {}, "FieldNames": ["Id"]}},
            headers={"Authorization": f"Bearer {oauth_token}", "Accept-Language": "ru"},
            timeout=10,
        )
        if validate_resp.status_code in (401, 403):
            return HTMLResponse(
                f"<html><body><h1>Ошибка: невалидный токен</h1>"
                f"<p>Код ответа: {validate_resp.status_code}</p>"
                f"<a href='/admin/integrations/{service}'>Назад</a></body></html>",
                status_code=400,
            )

    async with async_session_factory() as session:
        account = MCPYandexAccount(
            user_id=user.id,
            account_name=account_name or f"{login} ({service_type.value})",
            service_type=service_type,
            encrypted_access_token=crypto.encrypt(oauth_token),
            encrypted_refresh_token=None,
            token_expires_at=None,
            account_context=context or None,
            is_active=True,
        )
        session.add(account)
        await session.commit()

    return RedirectResponse(f"/admin/integrations/{service}", status_code=303)


@app.get("/admin/integrations/{service}/edit/{account_id}", response_class=HTMLResponse)
async def edit_account_page(service: str, account_id: int, request: Request):
    email = _user_email(request)
    user = await _get_or_create_user(email)
    async with async_session_factory() as session:
        result = await session.execute(
            select(MCPYandexAccount).where(
                MCPYandexAccount.id == account_id,
                MCPYandexAccount.user_id == user.id,
            )
        )
        account = result.scalar_one_or_none()

    if not account:
        return RedirectResponse(f"/admin/integrations/{service}")

    return templates.TemplateResponse(request, "edit_account.html", {
        "user_email": email,
        "service": service,
        "service_label": SERVICE_LABELS[ServiceType(service)],
        "account": account,
    })


@app.post("/admin/integrations/{service}/edit/{account_id}")
async def update_account(
    service: str,
    account_id: int,
    request: Request,
    account_name: str = Form(""),
    oauth_token: str = Form(""),
    context: str = Form(""),
):
    email = _user_email(request)
    user = await _get_or_create_user(email)
    async with async_session_factory() as session:
        result = await session.execute(
            select(MCPYandexAccount).where(
                MCPYandexAccount.id == account_id,
                MCPYandexAccount.user_id == user.id,
            )
        )
        account = result.scalar_one_or_none()
        if account:
            if account_name:
                account.account_name = account_name
            if oauth_token:
                account.encrypted_access_token = crypto.encrypt(oauth_token)
            account.account_context = context if context else None
            await session.commit()
    return RedirectResponse(f"/admin/integrations/{service}", status_code=303)


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
    ref = request.headers.get("Referer", "/admin/")
    return RedirectResponse(ref)


@app.get("/admin/ping")
async def ping():
    return {"status": "ok", "service": "yandex-admin"}
