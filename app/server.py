import http.server
import json
import mimetypes
import os
import urllib.parse
from http import cookies
from pathlib import Path

from app.config import HOST, PORT, COOKIE_NAME
from app.auth import authenticate_user, create_session, get_current_user, delete_session, seed_demo_users
from app.rbac import get_projects_for_user, get_project_by_id, get_user_tasks_summary
from app.ai_extractor import (
    get_directory_summary,
    extract_projects_from_transcript,
    validate_extracted_data,
    save_projects_and_tasks_atomic
)
from app.database import db_transaction, init_db

STATIC_DIR = Path(__file__).resolve().parent / "static"
SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"

class NovaWorksRequestHandler(http.server.BaseHTTPRequestHandler):
    """Production-grade HTTP request handler with REST API and static asset serving."""
    
    server_version = "NovaWorksCRM/1.0"

    def log_message(self, format, *args):
        # Concise logging
        print(f"[{self.log_date_time_string()}] {self.command} {self.path} - {format % args}")

    def send_json(self, data, status=200, extra_headers=None):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def send_error_json(self, message, status=400, details=None):
        payload = {"error": message}
        if details:
            payload["details"] = details
        self.send_json(payload, status=status)

    def get_auth_token(self):
        """Extracts session token from Cookie or Authorization header."""
        # 1. Check Authorization header
        auth_header = self.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:].strip()

        # 2. Check Cookie header
        cookie_header = self.headers.get("Cookie")
        if cookie_header:
            c = cookies.SimpleCookie()
            try:
                c.load(cookie_header)
                if COOKIE_NAME in c:
                    return c[COOKIE_NAME].value
            except Exception:
                pass
        return None

    def get_user_from_request(self):
        token = self.get_auth_token()
        if not token:
            return None
        return get_current_user(token)

    def read_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                return {}
            body_bytes = self.rfile.read(content_length)
            return json.loads(body_bytes.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Invalid JSON body: {str(e)}")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # REST API Routes
        if path.startswith("/api/"):
            self.handle_api_get(path, parsed)
            return

        # Static File Serving
        self.handle_static_get(path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            self.handle_api_post(path, parsed)
            return

        self.send_error_json("Not Found", 404)

    def handle_api_get(self, path: str, parsed):
        # 1. Get current logged-in user
        if path == "/api/auth/me":
            user = self.get_user_from_request()
            if not user:
                return self.send_error_json("Not authenticated", 401)
            return self.send_json({"user": user})

        # 2. Read-only Team Directory
        if path == "/api/users":
            user = self.get_user_from_request()
            if not user:
                return self.send_error_json("Authentication required", 401)
            directory = get_directory_summary()
            return self.send_json({"users": directory})

        # 3. Get Projects (Role-based access)
        if path == "/api/projects":
            user = self.get_user_from_request()
            if not user:
                return self.send_error_json("Authentication required", 401)
            projects = get_projects_for_user(user)
            return self.send_json({"projects": projects})

        # 4. Get Project by ID
        if path.startswith("/api/projects/"):
            project_id = path.split("/api/projects/")[1].strip()
            user = self.get_user_from_request()
            if not user:
                return self.send_error_json("Authentication required", 401)
            
            project = get_project_by_id(user, project_id)
            if not project:
                return self.send_error_json("Project not found or access denied", 403)
            return self.send_json({"project": project})

        # 5. Get User Tasks Summary (My Tasks screen)
        if path == "/api/tasks":
            user = self.get_user_from_request()
            if not user:
                return self.send_error_json("Authentication required", 401)
            tasks = get_user_tasks_summary(user)
            return self.send_json({"tasks": tasks})

        # 6. Sample Transcripts for easy testing in UI
        if path == "/api/sample-transcript":
            fpath = SAMPLE_DIR / "transcript.txt"
            content = fpath.read_text(encoding="utf-8") if fpath.exists() else ""
            return self.send_json({"transcript": content})

        if path == "/api/modified-transcript":
            fpath = SAMPLE_DIR / "modified_transcript.txt"
            content = fpath.read_text(encoding="utf-8") if fpath.exists() else ""
            return self.send_json({"transcript": content})

        return self.send_error_json("API route not found", 404)

    def handle_api_post(self, path: str, parsed):
        # 1. Login
        if path == "/api/auth/login":
            try:
                data = self.read_json_body()
            except ValueError as e:
                return self.send_error_json(str(e), 400)

            email = data.get("email", "")
            password = data.get("password", "")
            if not email or not password:
                return self.send_error_json("Email and password are required", 400)

            user = authenticate_user(email, password)
            if not user:
                return self.send_error_json("Invalid email or password", 401)

            token = create_session(user["id"])
            headers = {
                "Set-Cookie": f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax"
            }
            return self.send_json({
                "message": "Login successful",
                "token": token,
                "user": user
            }, 200, headers)

        # 2. Logout
        if path == "/api/auth/logout":
            token = self.get_auth_token()
            if token:
                delete_session(token)
            headers = {
                "Set-Cookie": f"{COOKIE_NAME}=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT"
            }
            return self.send_json({"message": "Logged out successfully"}, 200, headers)

        # 3. Create from Transcript (Admin only)
        if path == "/api/transcript/create":
            user = self.get_user_from_request()
            if not user:
                return self.send_error_json("Authentication required", 401)
            
            # RBAC: reject unless user.role == ADMIN
            if user.get("role") != "ADMIN":
                return self.send_error_json("Forbidden: Only administrators can create projects from transcripts", 403)

            try:
                data = self.read_json_body()
            except ValueError as e:
                return self.send_error_json(str(e), 400)

            transcript = data.get("transcript", "").strip()
            if not transcript:
                return self.send_error_json("Transcript cannot be empty", 400)

            directory = get_directory_summary()

            try:
                # Step 1: AI extraction (Dual-engine: LLM or Semantic NLP fallback)
                draft = extract_projects_from_transcript(transcript)
                
                # Step 2: Strict schema and constraint validation
                validation_errors = validate_extracted_data(draft, directory)
                if validation_errors:
                    return self.send_error_json(
                        "Validation failed: Unresolved or invalid fields detected",
                        status=422,
                        details=validation_errors
                    )

                # Step 3: All-or-nothing atomic save
                result = save_projects_and_tasks_atomic(draft)
                return self.send_json(result, 201)

            except Exception as e:
                return self.send_error_json(f"AI Transcript processing failed: {str(e)}", 500)

        # 4. Seed Demo Users
        if path == "/api/seed":
            count = seed_demo_users()
            return self.send_json({"message": f"Successfully seeded {count} demo accounts"})

        # 5. Reset Projects & Tasks
        if path == "/api/reset-data":
            user = self.get_user_from_request()
            if not user or user.get("role") != "ADMIN":
                return self.send_error_json("Only admin can reset demo project data", 403)
            with db_transaction() as conn:
                conn.execute("DELETE FROM tasks")
                conn.execute("DELETE FROM projects")
            return self.send_json({"message": "All projects and tasks cleared for fresh demonstration."})

        return self.send_error_json("API route not found", 404)

    def handle_static_get(self, path: str):
        if path == "/" or path == "":
            path = "/index.html"

        # Sanitize path
        file_path = (STATIC_DIR / path.lstrip("/")).resolve()
        
        # Security check: ensure path is inside STATIC_DIR
        if not str(file_path).startswith(str(STATIC_DIR)):
            self.send_error_json("Forbidden", 403)
            return

        if not file_path.exists() or file_path.is_dir():
            # Fallback to index.html for SPA routing
            file_path = STATIC_DIR / "index.html"

        if not file_path.exists():
            self.send_error_json("File not found", 404)
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = "application/octet-stream"

        try:
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8" if "text" in content_type or "json" in content_type else content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error_json(f"Error reading file: {str(e)}", 500)

def run_server():
    init_db()
    seed_demo_users()
    server_address = (HOST, PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, NovaWorksRequestHandler)
    print(f"\n=======================================================", flush=True)
    print(f"🚀 NovaWorks AI Project Management CRM is running!", flush=True)
    print(f"🔗 Local Web Application: http://{HOST}:{PORT}", flush=True)
    print(f"=======================================================\n", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
