import sys
import threading
import time
import json
import urllib.request
import urllib.parse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import PORT, HOST
from app.server import NovaWorksRequestHandler
from app.database import init_db
from app.auth import seed_demo_users
import http.server

def run_http_integration_test():
    print("==================================================")
    print("TEST: Full HTTP Server REST API Integration")
    print("==================================================")
    init_db()
    seed_demo_users()

    # Start server in a background thread on an alternate test port to avoid conflict
    test_port = 8089
    server = http.server.ThreadingHTTPServer(("127.0.0.1", test_port), NovaWorksRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    base_url = f"http://127.0.0.1:{test_port}"
    print(f"Test server running at {base_url}")

    try:
        # 1. Test Static Index Page
        print("\n1. Testing GET / (Static HTML)...")
        with urllib.request.urlopen(f"{base_url}/") as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "NovaWorks" in html
            print("✓ Static index.html served successfully.")

        # 2. Test Login API
        print("\n2. Testing POST /api/auth/login (Admin)...")
        login_payload = json.dumps({"email": "admin@novaworks.example", "password": "Demo123!"}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/auth/login", data=login_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            token = data["token"]
            assert data["user"]["role"] == "ADMIN"
            print(f"✓ Admin logged in. Token: {token[:8]}...")

        # 3. Test Team Directory
        print("\n3. Testing GET /api/users...")
        req = urllib.request.Request(f"{base_url}/api/users", headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            users = json.loads(resp.read().decode("utf-8"))["users"]
            assert len(users) == 10
            print(f"✓ Fetched {len(users)} demo users in directory.")

        # 4. Test Transcript Creation over HTTP
        print("\n4. Testing POST /api/transcript/create (Admin)...")
        transcript_text = (ROOT_DIR / "sample_data" / "transcript.txt").read_text(encoding="utf-8")
        trans_payload = json.dumps({"transcript": transcript_text}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/transcript/create", data=trans_payload, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        })
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 201
            res = json.loads(resp.read().decode("utf-8"))
            assert res["projectsCreated"] == 3
            assert res["tasksCreated"] == 12
            print(f"✓ Created {res['projectsCreated']} projects and {res['tasksCreated']} tasks via HTTP API.")

        # 5. Test Non-Admin Rejection (Agent trying to create from transcript)
        print("\n5. Testing RBAC Rejection for non-admin on transcript endpoint...")
        # Login as Ali (Agent)
        ali_payload = json.dumps({"email": "ali@novaworks.example", "password": "Demo123!"}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/auth/login", data=ali_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            ali_token = json.loads(resp.read().decode("utf-8"))["token"]

        try:
            req = urllib.request.Request(f"{base_url}/api/transcript/create", data=trans_payload, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ali_token}"
            })
            urllib.request.urlopen(req)
            assert False, "Should have failed with 403 Forbidden!"
        except urllib.error.HTTPError as e:
            assert e.code == 403
            print("✓ Non-admin correctly rejected with 403 Forbidden.")

        # 6. Test Agent Project Filtering
        print("\n6. Testing Agent Project Filtering...")
        req = urllib.request.Request(f"{base_url}/api/projects", headers={"Authorization": f"Bearer {ali_token}"})
        with urllib.request.urlopen(req) as resp:
            ali_projects = json.loads(resp.read().decode("utf-8"))["projects"]
            assert len(ali_projects) == 1
            assert ali_projects[0]["name"] == "UrbanCart Website"
            print("✓ Agent Ali correctly sees only UrbanCart Website.")

        print("\n==================================================")
        print("✓ ALL HTTP REST API INTEGRATION TESTS PASSED!")
        print("==================================================")

    finally:
        server.shutdown()

if __name__ == "__main__":
    run_http_integration_test()
