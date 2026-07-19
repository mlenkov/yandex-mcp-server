from admin.app import SERVICE_SCOPES
from app.models import ServiceType


def test_scopes_are_valid_yandex_names():
    valid_patterns = [
        "direct:api", "direct",
        "metrika:read", "metrika:api",
        "webmaster:api", "webmaster",
        "audience:api",
        "admetrica:api", "appmetrica:api",
    ]
    for service, scope in SERVICE_SCOPES.items():
        assert any(scope.startswith(p.split(":")[0]) for p in valid_patterns), \
            f"Invalid scope for {service}: {scope}"


def test_all_services_have_scopes():
    for st in ServiceType:
        assert st in SERVICE_SCOPES, f"Missing scope for {st}"
