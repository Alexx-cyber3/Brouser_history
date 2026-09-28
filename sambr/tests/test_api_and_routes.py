import json
from app.models.case import Case

def test_login_flow(client):
    # Failed login
    res = client.post("/login", data={"username": "admin", "password": "wrongpassword"}, follow_redirects=True)
    assert b"Invalid investigator credentials" in res.data

    # Successful login
    res2 = client.post("/login", data={"username": "admin", "password": "forensic2026"}, follow_redirects=True)
    assert b"TRACEFUSION" in res2.data
    assert b"Dashboard" in res2.data

def test_case_creation_flow(auth_client, app):
    res = auth_client.post("/cases", data={
        "case_number": "TF-ROUTE-001",
        "title": "Route Verification Case",
        "investigator_name": "Agent Smith",
        "organization": "DFIR Unit",
        "description": "Testing route handling."
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"TF-ROUTE-001" in res.data

    with app.app_context():
        c = Case.query.filter_by(case_number="TF-ROUTE-001").first()
        assert c is not None
        assert c.title == "Route Verification Case"

def test_api_cases_endpoint(auth_client):
    res = auth_client.get("/api/cases")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

def test_case_switch_and_smart_redirect(auth_client, app):
    with app.app_context():
        from app.extensions import db
        case1 = Case(case_number="TF-SW-001", title="Switch Case 1", investigator_name="Examiner", organization="Unit")
        case2 = Case(case_number="TF-SW-002", title="Switch Case 2", investigator_name="Examiner", organization="Unit")
        db.session.add_all([case1, case2])
        db.session.commit()
        id1, id2 = case1.id, case2.id

    # Switch to case 1 via GET
    res = auth_client.get(f"/cases/{id1}/select", follow_redirects=False)
    assert res.status_code == 302

    # Switch to case 2 while referrer was on case 1 timeline
    res2 = auth_client.get(f"/cases/{id2}/select", headers={"Referer": f"http://localhost/cases/{id1}/timeline"}, follow_redirects=False)
    assert res2.status_code == 302
    assert f"/cases/{id2}/timeline" in res2.headers["Location"]
