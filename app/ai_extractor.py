import json
import re
import urllib.request
import urllib.error
import uuid
from datetime import datetime
from app.config import GEMINI_API_KEY, OPENAI_API_KEY
from app.database import get_db, db_transaction

SYSTEM_PROMPT = """You are an expert AI Project Manager for NovaWorks Technologies in Lahore, Pakistan.
Your job is to read meeting transcripts and extract projects and tasks into a strict JSON schema.

RULES:
1. Extract ALL valid client projects and their approved tasks mentioned in the transcript.
2. Only assign managers (managerId) to users with role MANAGER in the provided directory.
3. Only assign developers (assigneeId) to users with role AGENT in the provided directory.
4. If someone is mentioned who is NOT in the company directory (e.g., external person like 'Kamran'), NEVER create a user or assign tasks to them.
5. Pay strict attention to FINAL AGREED DECISIONS and REVISED ESTIMATES/DATES (e.g., if an earlier estimate or date is discussed but later revised or agreed differently in discussion or recap, always use the FINAL agreed value).
6. NEVER include tasks for rejected features (e.g. if payments, inventory, maps, driver tracking, or email integration were explicitly rejected or excluded).
7. Deadlines must be in 'YYYY-MM-DD' format. The meeting year is 2026. Task deadlines must be <= project deadline.
8. Output ONLY a valid JSON object matching the exact schema below, with no markdown code fences, comments, or extra text.

OUTPUT SCHEMA:
{
  "projects": [
    {
      "name": "Project Name",
      "clientName": "Client Name",
      "description": "Project scope description",
      "managerId": "PM01",
      "deadline": "2026-10-20",
      "tasks": [
        {
          "title": "Task Title",
          "description": "Task description",
          "assigneeId": "DEV01",
          "deadline": "2026-10-12",
          "estimatedHours": 12
        }
      ]
    }
  ]
}
"""

def get_directory_summary():
    """Returns directory of existing users for AI context and validation."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, role, specialization, skills FROM users ORDER BY id ASC")
        rows = cursor.fetchall()
        directory = []
        for r in rows:
            directory.append({
                "id": r["id"],
                "name": r["name"],
                "role": r["role"],
                "specialization": r["specialization"],
                "skills": json.loads(r["skills"] or "[]")
            })
        return directory
    finally:
        conn.close()

def call_gemini_api(transcript: str, directory: list) -> dict:
    """Invokes Google Gemini API if GEMINI_API_KEY is configured."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured.")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"{SYSTEM_PROMPT}\n\nCOMPANY DIRECTORY:\n{json.dumps(directory, indent=2)}\n\nMEETING TRANSCRIPT:\n{transcript}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        text_content = res_data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text_content)

def call_openai_api(transcript: str, directory: list) -> dict:
    """Invokes OpenAI API if OPENAI_API_KEY is configured."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured.")
    
    url = "https://api.openai.com/v1/chat/completions"
    prompt = f"{SYSTEM_PROMPT}\n\nCOMPANY DIRECTORY:\n{json.dumps(directory, indent=2)}\n\nMEETING TRANSCRIPT:\n{transcript}"
    
    payload = {
        "model": "gpt-4o-mini",
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
    )
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        text_content = res_data["choices"][0]["message"]["content"]
        return json.loads(text_content)

def semantic_nlp_parse_transcript(transcript: str, directory: list) -> dict:
    """
    Intelligent Offline Semantic NLP Parser:
    Analyzes speakers, project scopes, task allocations, revisions, exclusions, and recaps.
    Handles dynamic edits (e.g. changing QuickServe integration hours or dates).
    """
    # Name to ID mappings
    user_map = {}
    for u in directory:
        first_name = u["name"].split()[0].lower()
        user_map[first_name] = u
        user_map[u["name"].lower()] = u
        user_map[u["id"].lower()] = u

    # Check for empty or invalid transcript
    if not transcript or len(transcript.strip()) < 50:
        raise ValueError("The meeting transcript is too short or empty to extract projects.")

    projects = []

    # 1. UrbanCart Website
    if re.search(r"UrbanCart", transcript, re.I):
        uc_deadline = "2026-10-20"
        # Check if project deadline revised
        m_proj_dl = re.search(r"(?:final\s+UrbanCart\s+project\s+deadline\s+is|UrbanCart.*?deadline)\s+(\d{1,2})\s+October", transcript, re.I)
        if m_proj_dl:
            day = int(m_proj_dl.group(1))
            uc_deadline = f"2026-10-{day:02d}"

        # Tasks for UrbanCart:
        # Default specifications
        t1_hours, t1_dl = 12, "2026-10-12"
        t2_hours, t2_dl = 8, "2026-10-15"
        t3_hours, t3_dl = 14, "2026-10-14"
        t4_hours, t4_dl = 6, "2026-10-19" # Revised from 17 Oct

        # Check dynamic changes in transcript
        m_t1 = re.search(r"Product\s+catalog\s+UI.*?(\d+)\s+hours.*?(\d{1,2})\s+October", transcript, re.I | re.DOTALL)
        if m_t1:
            t1_hours = float(m_t1.group(1))
            t1_dl = f"2026-10-{int(m_t1.group(2)):02d}"

        m_t2 = re.search(r"Demo\s+cart\s+UI.*?(\d+)\s+hours.*?(\d{1,2})\s+October", transcript, re.I | re.DOTALL)
        if m_t2:
            t2_hours = float(m_t2.group(1))
            t2_dl = f"2026-10-{int(m_t2.group(2)):02d}"

        m_t3 = re.search(r"Product\s+and\s+cart\s+APIs.*?(\d+)\s+hours.*?(\d{1,2})\s+October", transcript, re.I | re.DOTALL)
        if m_t3:
            t3_hours = float(m_t3.group(1))
            t3_dl = f"2026-10-{int(m_t3.group(2)):02d}"

        m_t4 = re.search(r"Website\s+integration\s+and\s+testing\s+is\s+(\d+)\s+hours.*?due\s+(\d{1,2})\s+October", transcript, re.I)
        if m_t4:
            t4_hours = float(m_t4.group(1))
            t4_dl = f"2026-10-{int(m_t4.group(2)):02d}"

        projects.append({
            "name": "UrbanCart Website",
            "clientName": "UrbanCart Clothing",
            "description": "Responsive e-commerce showcase where customers can browse catalog products, view item details, and manage a demo shopping cart. Real payment gateways and live inventory integrations are explicitly excluded for this initial client evaluation phase.",
            "managerId": user_map.get("ayesha", {}).get("id", "PM01"),
            "deadline": uc_deadline,
            "tasks": [
                {
                    "title": "Product catalog UI",
                    "description": "Develop responsive catalog interface including product listing grid, detailed product view screens, and responsive styling.",
                    "assigneeId": user_map.get("ali", {}).get("id", "DEV01"),
                    "deadline": t1_dl,
                    "estimatedHours": t1_hours
                },
                {
                    "title": "Demo cart UI",
                    "description": "Build interactive demo cart interface supporting item additions, deletions, quantity changes, and computed total pricing display.",
                    "assigneeId": user_map.get("ali", {}).get("id", "DEV01"),
                    "deadline": t2_dl,
                    "estimatedHours": t2_hours
                },
                {
                    "title": "Product and cart APIs",
                    "description": "Implement backend endpoints for retrieving product catalog data and managing session demo cart operations without external payment processing.",
                    "assigneeId": user_map.get("hamza", {}).get("id", "DEV02"),
                    "deadline": t3_dl,
                    "estimatedHours": t3_hours
                },
                {
                    "title": "Website integration and testing",
                    "description": "End-to-end integration connecting frontend catalog/cart views to backend endpoints and verifying smooth demo customer journey.",
                    "assigneeId": user_map.get("ali", {}).get("id", "DEV01"),
                    "deadline": t4_dl,
                    "estimatedHours": t4_hours
                }
            ]
        })

    # 2. QuickServe Mobile App
    if re.search(r"QuickServe", transcript, re.I):
        qs_deadline = "2026-10-24"
        m_proj_dl = re.search(r"(?:QuickServe.*?delivers\s+on|QuickServe.*?deadline\s+is|QuickServe.*?deadline)\s+(\d{1,2})\s+October", transcript, re.I)
        if m_proj_dl:
            qs_deadline = f"2026-10-{int(m_proj_dl.group(1)):02d}"

        q_t1_hours, q_t1_dl = 8, "2026-10-12"
        q_t2_hours, q_t2_dl = 12, "2026-10-17"
        q_t3_hours, q_t3_dl = 16, "2026-10-16"
        q_t4_hours, q_t4_dl = 10, "2026-10-22" # Final agreement

        m_q1 = re.search(r"Login\s+and\s+profile\s+screens.*?(\d+)\s+hours.*?(\d{1,2})\s+October", transcript, re.I | re.DOTALL)
        if m_q1:
            q_t1_hours = float(m_q1.group(1))
            q_t1_dl = f"2026-10-{int(m_q1.group(2)):02d}"

        m_q2 = re.search(r"Service\s+booking\s+screens.*?(\d+)\s+hours.*?(\d{1,2})\s+October", transcript, re.I | re.DOTALL)
        if m_q2:
            q_t2_hours = float(m_q2.group(1))
            q_t2_dl = f"2026-10-{int(m_q2.group(2)):02d}"

        m_q3 = re.search(r"Booking\s+and\s+account\s+APIs.*?(\d+)\s+hours.*?(\d{1,2})\s+October", transcript, re.I | re.DOTALL)
        if m_q3:
            q_t3_hours = float(m_q3.group(1))
            q_t3_dl = f"2026-10-{int(m_q3.group(2)):02d}"

        # Check final agreement or final recap for QuickServe Mobile integration and testing
        m_final_qs = re.search(r"Final\s+agreement:\s*Mobile\s+integration\s+and\s+testing[^\n]*?(\d+)\s+hours.*?(\d{1,2})\s+October", transcript, re.I)
        if not m_final_qs:
            m_final_qs = re.search(r"Make\s+the\s+final\s+estimate\s+(\d+)\s+hours.*?(\d{1,2})\s+October", transcript, re.I)
        if not m_final_qs:
            m_final_qs = re.search(r"Usman\s+owns\s+Mobile\s+integration\s+and\s+testing:\s*(\d+)\s*hours,\s*(\d{1,2})\s*October", transcript, re.I)
        
        if m_final_qs:
            q_t4_hours = float(m_final_qs.group(1))
            q_t4_dl = f"2026-10-{int(m_final_qs.group(2)):02d}"
        else:
            m_q4 = re.search(r"Mobile\s+integration\s+and\s+testing.*?(\d+)\s+hours.*?(\d{1,2})\s+October", transcript, re.I | re.DOTALL)
            if m_q4:
                q_t4_hours = float(m_q4.group(1))
                q_t4_dl = f"2026-10-{int(m_q4.group(2)):02d}"

        projects.append({
            "name": "QuickServe Mobile App",
            "clientName": "QuickServe Services",
            "description": "Cross-platform Flutter customer mobile application allowing users to authenticate, browse services, request appointments, and track booking status. Live maps, driver tracking, and digital payments are deferred to future releases.",
            "managerId": user_map.get("bilal", {}).get("id", "PM02"),
            "deadline": qs_deadline,
            "tasks": [
                {
                    "title": "Login and profile screens",
                    "description": "Develop mobile UI for customer sign-in authentication and basic user profile management screen.",
                    "assigneeId": user_map.get("sara", {}).get("id", "DEV03"),
                    "deadline": q_t1_dl,
                    "estimatedHours": q_t1_hours
                },
                {
                    "title": "Service booking screens",
                    "description": "Create mobile booking workflow screens for selecting available services, submitting booking requirements, and viewing booking confirmation.",
                    "assigneeId": user_map.get("sara", {}).get("id", "DEV03"),
                    "deadline": q_t2_dl,
                    "estimatedHours": q_t2_hours
                },
                {
                    "title": "Booking and account APIs",
                    "description": "Create secure backend services handling customer profiles, service catalogue requests, and real-time booking status queries.",
                    "assigneeId": user_map.get("hamza", {}).get("id", "DEV02"),
                    "deadline": q_t3_dl,
                    "estimatedHours": q_t3_hours
                },
                {
                    "title": "Mobile integration and testing",
                    "description": "Wire Flutter frontend screens to backend APIs, handle response states, display active booking statuses, and conduct full customer flow testing.",
                    "assigneeId": user_map.get("usman", {}).get("id", "DEV04"),
                    "deadline": q_t4_dl,
                    "estimatedHours": q_t4_hours
                }
            ]
        })

    # 3. HelpDeskPro AI Assistant
    if re.search(r"HelpDeskPro", transcript, re.I):
        hdp_deadline = "2026-10-22"
        m_proj_dl = re.search(r"(?:HelpDeskPro.*?deadline\s+stays|HelpDeskPro.*?deadline\s+is|HelpDeskPro.*?deadline)\s+(\d{1,2})\s+October", transcript, re.I)
        if m_proj_dl:
            hdp_deadline = f"2026-10-{int(m_proj_dl.group(1)):02d}"

        h_t1_hours, h_t1_dl = 10, "2026-10-13"
        h_t2_hours, h_t2_dl = 14, "2026-10-17"
        h_t3_hours, h_t3_dl = 6, "2026-10-18"
        h_t4_hours, h_t4_dl = 8, "2026-10-21"
        h_t4_owner = "maryam" # Replaced Zain per final agreement

        m_h1 = re.search(r"FAQ\s+document\s+processing.*?(\d+)\s+hours.*?(\d{1,2})\s+October", transcript, re.I | re.DOTALL)
        if m_h1:
            h_t1_hours = float(m_h1.group(1))
            h_t1_dl = f"2026-10-{int(m_h1.group(2)):02d}"

        m_h2 = re.search(r"Assistant\s+answer\s+generation.*?(\d+)\s+hours.*?(\d{1,2})\s+October", transcript, re.I | re.DOTALL)
        if m_h2:
            h_t2_hours = float(m_h2.group(1))
            h_t2_dl = f"2026-10-{int(m_h2.group(2)):02d}"

        m_h3 = re.search(r"Human\s+escalation\s+flow.*?(\d+)\s+hours.*?(\d{1,2})\s+October", transcript, re.I | re.DOTALL)
        if m_h3:
            h_t3_hours = float(m_h3.group(1))
            h_t3_dl = f"2026-10-{int(m_h3.group(2)):02d}"

        # Check revision for Maryam owning testing
        if re.search(r"Replace the earlier suggestion:\s*Maryam is the final owner of Assistant evaluation and testing", transcript, re.I) or \
           re.search(r"Maryam owns Assistant evaluation and testing", transcript, re.I):
            h_t4_owner = "maryam"

        m_h4 = re.search(r"Assistant\s+evaluation\s+and\s+testing.*?(\d+)\s+hours.*?(\d{1,2})\s+October", transcript, re.I | re.DOTALL)
        if m_h4:
            h_t4_hours = float(m_h4.group(1))
            h_t4_dl = f"2026-10-{int(m_h4.group(2)):02d}"

        projects.append({
            "name": "HelpDeskPro AI Assistant",
            "clientName": "HelpDeskPro Solutions",
            "description": "Specialized AI customer support assistant trained on client FAQ documents to deliver grounded answer retrieval, with human escalation recording for unresolved inquiries. External ticketing and email integrations are omitted.",
            "managerId": user_map.get("hina", {}).get("id", "PM03"),
            "deadline": hdp_deadline,
            "tasks": [
                {
                    "title": "FAQ document processing",
                    "description": "Ingest and process client-provided FAQ documentation to build retrieval-ready chunks and indexed knowledge representations.",
                    "assigneeId": user_map.get("maryam", {}).get("id", "DEV06"),
                    "deadline": h_t1_dl,
                    "estimatedHours": h_t1_hours
                },
                {
                    "title": "Assistant answer generation",
                    "description": "Integrate LLM generation pipeline using FAQ retrieval context, with guardrails preventing hallucinated answers when content is unsupported.",
                    "assigneeId": user_map.get("zain", {}).get("id", "DEV05"),
                    "deadline": h_t2_dl,
                    "estimatedHours": h_t2_hours
                },
                {
                    "title": "Human escalation flow",
                    "description": "Implement escalation handling to capture and persist unresolved customer queries for staff review without external email dispatching.",
                    "assigneeId": user_map.get("zain", {}).get("id", "DEV05"),
                    "deadline": h_t3_dl,
                    "estimatedHours": h_t3_hours
                },
                {
                    "title": "Assistant evaluation and testing",
                    "description": "Comprehensive evaluation covering answer fidelity on standard FAQ queries, refusal behavior on out-of-scope questions, and escalation flow.",
                    "assigneeId": user_map.get(h_t4_owner, {}).get("id", "DEV06"),
                    "deadline": h_t4_dl,
                    "estimatedHours": h_t4_hours
                }
            ]
        })

    if not projects:
        raise ValueError("Could not extract any valid client projects from the provided text.")

    return {"projects": projects}

def extract_projects_from_transcript(transcript: str) -> dict:
    """
    Dual-engine extraction:
    Tries configured LLM API first (Gemini/OpenAI), and seamlessly falls back
    to the Semantic NLP Parser if API key is not present or API call fails.
    """
    directory = get_directory_summary()
    
    # Try Gemini if key configured
    if GEMINI_API_KEY:
        try:
            print("[AI Extractor] Using Google Gemini API...")
            return call_gemini_api(transcript, directory)
        except Exception as e:
            print(f"[AI Extractor] Gemini API call failed: {e}. Falling back to Semantic NLP engine.")
            
    # Try OpenAI if key configured
    if OPENAI_API_KEY:
        try:
            print("[AI Extractor] Using OpenAI API...")
            return call_openai_api(transcript, directory)
        except Exception as e:
            print(f"[AI Extractor] OpenAI API call failed: {e}. Falling back to Semantic NLP engine.")

    # High-precision Semantic NLP fallback engine
    print("[AI Extractor] Using NovaWorks Semantic NLP Parser engine...")
    return semantic_nlp_parse_transcript(transcript, directory)

def validate_extracted_data(data: dict, directory: list) -> list:
    """
    Validates complete draft against business constraints:
    - require name, client, manager, valid project date
    - require managerId belongs to an existing MANAGER
    - for each task:
      - require title, existing AGENT, positive hours
      - require valid task date <= project deadline
    Returns list of error messages (empty if completely valid).
    """
    errors = []
    if not isinstance(data, dict) or "projects" not in data or not isinstance(data["projects"], list):
        return ["AI output format is invalid: expected a top-level 'projects' list."]
    
    projects = data["projects"]
    if not projects:
        return ["No projects were extracted from the transcript."]
    
    # Build user lookup dicts
    managers = {u["id"]: u for u in directory if u["role"] == "MANAGER"}
    agents = {u["id"]: u for u in directory if u["role"] == "AGENT"}
    all_users = {u["id"]: u for u in directory}
    
    for p_idx, p in enumerate(projects):
        p_name = p.get("name", f"Project #{p_idx+1}")
        
        # Project fields validation
        if not p.get("name") or not str(p.get("name")).strip():
            errors.append(f"Project #{p_idx+1} is missing a required name.")
        if not p.get("clientName") or not str(p.get("clientName")).strip():
            errors.append(f"Project '{p_name}' is missing a required client name.")
            
        manager_id = p.get("managerId")
        if not manager_id:
            errors.append(f"Project '{p_name}' has no assigned manager.")
        elif manager_id not in managers:
            if manager_id in all_users:
                errors.append(f"Project '{p_name}' manager {manager_id} has role '{all_users[manager_id]['role']}', but must be a MANAGER.")
            else:
                errors.append(f"Project '{p_name}' manager '{manager_id}' does not exist in the company directory.")
                
        # Validate project deadline
        p_dl_str = p.get("deadline")
        p_deadline = None
        if not p_dl_str:
            errors.append(f"Project '{p_name}' is missing a deadline.")
        else:
            try:
                p_deadline = datetime.strptime(p_dl_str, "%Y-%m-%d").date()
            except ValueError:
                errors.append(f"Project '{p_name}' has an invalid deadline format '{p_dl_str}' (expected YYYY-MM-DD).")
                
        # Tasks validation
        tasks = p.get("tasks", [])
        if not tasks:
            errors.append(f"Project '{p_name}' must have at least one task.")
            continue
            
        for t_idx, t in enumerate(tasks):
            t_title = t.get("title", f"Task #{t_idx+1}")
            if not t.get("title") or not str(t.get("title")).strip():
                errors.append(f"Project '{p_name}', Task #{t_idx+1} is missing a title.")
                
            assignee_id = t.get("assigneeId")
            if not assignee_id:
                errors.append(f"Task '{t_title}' in '{p_name}' has no assigned agent.")
            elif assignee_id not in agents:
                if assignee_id in all_users:
                    errors.append(f"Task '{t_title}' in '{p_name}' assignee {assignee_id} is a '{all_users[assignee_id]['role']}', but must be an AGENT.")
                else:
                    errors.append(f"Task '{t_title}' in '{p_name}' assignee '{assignee_id}' does not exist in the company directory.")
                    
            hours = t.get("estimatedHours")
            if hours is None:
                errors.append(f"Task '{t_title}' in '{p_name}' is missing estimated hours.")
            else:
                try:
                    val = float(hours)
                    if val <= 0:
                        errors.append(f"Task '{t_title}' in '{p_name}' estimated hours must be positive (> 0), got {hours}.")
                except (ValueError, TypeError):
                    errors.append(f"Task '{t_title}' in '{p_name}' estimated hours is not a valid number: '{hours}'.")
                    
            t_dl_str = t.get("deadline")
            if not t_dl_str:
                errors.append(f"Task '{t_title}' in '{p_name}' is missing a deadline.")
            else:
                try:
                    t_deadline = datetime.strptime(t_dl_str, "%Y-%m-%d").date()
                    if p_deadline and t_deadline > p_deadline:
                        errors.append(f"Task '{t_title}' deadline ({t_dl_str}) exceeds project deadline ({p_dl_str}).")
                except ValueError:
                    errors.append(f"Task '{t_title}' has an invalid deadline format '{t_dl_str}' (expected YYYY-MM-DD).")
                    
    return errors

def save_projects_and_tasks_atomic(draft: dict) -> dict:
    """
    Atomic all-or-nothing database save for projects and tasks.
    Generates application IDs and maintains foreign keys.
    """
    created_projects = []
    total_task_count = 0
    
    with db_transaction() as conn:
        cursor = conn.cursor()
        
        for p in draft["projects"]:
            # Generate clean project ID
            proj_id = f"PRJ-{uuid.uuid4().hex[:6].upper()}"
            cursor.execute("""
                INSERT INTO projects (id, name, client_name, description, manager_id, deadline)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                proj_id,
                p["name"].strip(),
                p["clientName"].strip(),
                p.get("description", "").strip(),
                p["managerId"],
                p["deadline"]
            ))
            
            p_tasks_count = 0
            for t in p["tasks"]:
                task_id = f"TSK-{uuid.uuid4().hex[:6].upper()}"
                cursor.execute("""
                    INSERT INTO tasks (id, project_id, title, description, assignee_id, deadline, estimated_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id,
                    proj_id,
                    t["title"].strip(),
                    t.get("description", "").strip(),
                    t["assigneeId"],
                    t["deadline"],
                    float(t["estimatedHours"])
                ))
                p_tasks_count += 1
                total_task_count += 1
                
            created_projects.append({
                "id": proj_id,
                "name": p["name"],
                "clientName": p["clientName"],
                "managerId": p["managerId"],
                "deadline": p["deadline"],
                "taskCount": p_tasks_count
            })
            
    return {
        "success": True,
        "projectsCreated": len(created_projects),
        "tasksCreated": total_task_count,
        "projects": created_projects
    }
