from app.main import app


def test_workflow_meeting_routes_exist():
    routes = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes if hasattr(route, "path")}

    assert ("/workflow/meetings", ("POST",)) in routes
    assert ("/workflow/meetings", ("GET", "HEAD")) in routes or ("/workflow/meetings", ("GET",)) in routes


def test_workflow_oauth_routes_exist():
    routes = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes if hasattr(route, "path")}

    assert ("/workflow/oauth/{provider}/start", ("GET", "HEAD")) in routes or ("/workflow/oauth/{provider}/start", ("GET",)) in routes
    assert ("/workflow/oauth/{provider}/callback", ("GET", "HEAD")) in routes or ("/workflow/oauth/{provider}/callback", ("GET",)) in routes
