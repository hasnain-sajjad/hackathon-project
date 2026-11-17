import sys
import json
from pathlib import Path

# Add project root
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.database import init_db, db_transaction, get_db
from app.auth import seed_demo_users, authenticate_user, create_session, get_current_user
from app.rbac import get_projects_for_user, get_project_by_id, get_tasks_for_project, get_user_tasks_summary
from app.ai_extractor import (
    get_directory_summary,
    extract_projects_from_transcript,
    validate_extracted_data,
    save_projects_and_tasks_atomic
)

def run_tests():
    print("=" * 60)
    print("RUNNING COMPREHENSIVE NOVAWORKS CRM TEST SUITE")
    print("=" * 60)
    
    # 1. Database Init and Seed
    print("\n[TEST 1] Database Initialization and Seeding...")
    init_db()
    count = seed_demo_users()
    assert count == 10, f"Expected 10 users, got {count}"
    print("✓ Successfully initialized database and seeded 10 accounts.")
    
    # 2. Authentication Verification
    print("\n[TEST 2] Authentication and Passwords...")
    admin = authenticate_user("admin@novaworks.example", "Demo123!")
    assert admin is not None, "Admin authentication failed"
    assert admin["role"] == "ADMIN", f"Expected ADMIN, got {admin['role']}"
    
    ayesha = authenticate_user("ayesha@novaworks.example", "Demo123!")
    assert ayesha is not None, "Ayesha authentication failed"
    assert ayesha["role"] == "MANAGER"
    
    ali = authenticate_user("ali@novaworks.example", "Demo123!")
    assert ali is not None, "Ali authentication failed"
    assert ali["role"] == "AGENT"
    
    # Invalid password test
    bad = authenticate_user("admin@novaworks.example", "WrongPassword")
    assert bad is None, "Bad password should return None"
    print("✓ Authentication verified for ADMIN, MANAGER, and AGENT roles.")

    # 3. Transcript Processing & AI Extraction
    print("\n[TEST 3] AI Transcript Extraction from Supplied Transcript...")
    transcript_path = ROOT_DIR / "sample_data" / "transcript.txt"
    transcript_text = transcript_path.read_text(encoding="utf-8")
    
    directory = get_directory_summary()
    draft = extract_projects_from_transcript(transcript_text)
    
    # Validation checks
    val_errors = validate_extracted_data(draft, directory)
    assert len(val_errors) == 0, f"Draft validation failed with errors: {val_errors}"
    print("✓ Extracted draft passed all schema and constraint validations.")
    
    # Save atomically to DB
    # Clear previous projects/tasks first
    with db_transaction() as conn:
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM projects")
        
    save_result = save_projects_and_tasks_atomic(draft)
    assert save_result["projectsCreated"] == 3, f"Expected 3 projects, got {save_result['projectsCreated']}"
    assert save_result["tasksCreated"] == 12, f"Expected 12 tasks, got {save_result['tasksCreated']}"
    print(f"✓ Saved {save_result['projectsCreated']} projects and {save_result['tasksCreated']} tasks atomically.")

    # 4. Verification of Specific Business Rules & Revisions
    print("\n[TEST 4] Verifying Business Logic, Revisions, and Exclusions...")
    conn = get_db()
    cursor = conn.cursor()
    
    # Check UrbanCart Website
    cursor.execute("SELECT * FROM projects WHERE name LIKE '%UrbanCart%'")
    uc_proj = cursor.fetchone()
    assert uc_proj is not None, "UrbanCart project missing"
    assert uc_proj["deadline"] == "2026-10-20", f"Expected UrbanCart deadline 2026-10-20, got {uc_proj['deadline']}"
    assert uc_proj["manager_id"] == "PM01", f"Expected manager PM01 (Ayesha), got {uc_proj['manager_id']}"
    
    # Check UrbanCart Tasks
    cursor.execute("SELECT * FROM tasks WHERE project_id = ? ORDER BY deadline ASC", (uc_proj["id"],))
    uc_tasks = cursor.fetchall()
    assert len(uc_tasks) == 4, f"Expected 4 tasks for UrbanCart, got {len(uc_tasks)}"
    
    # Task 4: Website integration and testing revised date
    cursor.execute("SELECT * FROM tasks WHERE project_id = ? AND title LIKE '%integration and testing%'", (uc_proj["id"],))
    uc_integ = cursor.fetchone()
    assert uc_integ["deadline"] == "2026-10-19", f"Expected UrbanCart integration deadline 2026-10-19, got {uc_integ['deadline']}"
    assert float(uc_integ["estimated_hours"]) == 6.0, f"Expected 6 hours, got {uc_integ['estimated_hours']}"
    assert uc_integ["assignee_id"] == "DEV01", f"Expected assignee DEV01 (Ali), got {uc_integ['assignee_id']}"
    
    # Check QuickServe Mobile App
    cursor.execute("SELECT * FROM projects WHERE name LIKE '%QuickServe%'")
    qs_proj = cursor.fetchone()
    assert qs_proj["deadline"] == "2026-10-24"
    assert qs_proj["manager_id"] == "PM02" # Bilal
    
    cursor.execute("SELECT * FROM tasks WHERE project_id = ? AND title LIKE '%Mobile integration and testing%'", (qs_proj["id"],))
    qs_integ = cursor.fetchone()
    assert float(qs_integ["estimated_hours"]) == 10.0, f"Expected QuickServe integration 10 hours, got {qs_integ['estimated_hours']}"
    assert qs_integ["deadline"] == "2026-10-22", f"Expected deadline 2026-10-22, got {qs_integ['deadline']}"
    assert qs_integ["assignee_id"] == "DEV04", f"Expected assignee DEV04 (Usman), got {qs_integ['assignee_id']}"
    
    # Check HelpDeskPro
    cursor.execute("SELECT * FROM projects WHERE name LIKE '%HelpDeskPro%'")
    hdp_proj = cursor.fetchone()
    assert hdp_proj["deadline"] == "2026-10-22"
    assert hdp_proj["manager_id"] == "PM03" # Hina
    
    cursor.execute("SELECT * FROM tasks WHERE project_id = ? AND title LIKE '%Assistant evaluation and testing%'", (hdp_proj["id"],))
    hdp_eval = cursor.fetchone()
    assert hdp_eval["assignee_id"] == "DEV06", f"Expected assignee DEV06 (Maryam), got {hdp_eval['assignee_id']}"
    assert float(hdp_eval["estimated_hours"]) == 8.0
    assert hdp_eval["deadline"] == "2026-10-21"
    
    # Check that Kamran is NOT in users or assignees
    cursor.execute("SELECT * FROM users WHERE LOWER(name) LIKE '%kamran%'")
    assert cursor.fetchone() is None, "Kamran must not be in users table!"
    cursor.execute("SELECT * FROM tasks WHERE LOWER(title) LIKE '%payment%' OR LOWER(title) LIKE '%inventory%' OR LOWER(title) LIKE '%map%'")
    assert cursor.fetchone() is None, "Rejected tasks (payments/inventory/maps) should not be created!"
    conn.close()
    print("✓ All business rules, revisions, and exclusions verified against Organizer Verification Reference.")

    # 5. RBAC Access Control Tests
    print("\n[TEST 5] Testing Strict Role-Based Access Control (RBAC)...")
    
    # 5a. Admin sees all 3 projects and all 12 tasks
    admin_projs = get_projects_for_user(admin)
    assert len(admin_projs) == 3, f"Admin should see 3 projects, got {len(admin_projs)}"
    admin_tasks = get_user_tasks_summary(admin)
    assert len(admin_tasks) == 12, f"Admin should see 12 tasks, got {len(admin_tasks)}"
    print("✓ Admin has full access to all projects and tasks.")
    
    # 5b. Manager Ayesha (PM01) sees ONLY UrbanCart
    ayesha_projs = get_projects_for_user(ayesha)
    assert len(ayesha_projs) == 1, f"Ayesha should see 1 project, got {len(ayesha_projs)}"
    assert ayesha_projs[0]["name"] == "UrbanCart Website"
    
    # Manager Ayesha trying to access QuickServe project details directly
    ayesha_qs_access = get_project_by_id(ayesha, qs_proj["id"])
    assert ayesha_qs_access is None, "Manager Ayesha should be REJECTED from accessing QuickServe project details!"
    print("✓ Manager isolation verified (Ayesha sees only UrbanCart; cannot access QuickServe).")
    
    # 5c. Agent Ali (DEV01)
    ali_projs = get_projects_for_user(ali)
    assert len(ali_projs) == 1, f"Ali should see 1 project, got {len(ali_projs)}"
    assert ali_projs[0]["name"] == "UrbanCart Website"
    
    # Check tasks visible to Ali in UrbanCart
    ali_proj_detail = get_project_by_id(ali, uc_proj["id"])
    assert ali_proj_detail is not None
    assert len(ali_proj_detail["tasks"]) == 3, f"Ali should only see his 3 tasks, got {len(ali_proj_detail['tasks'])}"
    for t in ali_proj_detail["tasks"]:
        assert t["assigneeId"] == "DEV01", f"Ali saw task assigned to {t['assigneeId']}!"
    print("✓ Agent Ali isolation verified (sees only UrbanCart and only his 3 tasks, Hamza's task hidden).")
    
    # 5d. Agent Hamza (DEV02) - has tasks across UrbanCart AND QuickServe
    hamza = authenticate_user("hamza@novaworks.example", "Demo123!")
    hamza_projs = get_projects_for_user(hamza)
    assert len(hamza_projs) == 2, f"Hamza should see 2 projects, got {len(hamza_projs)}"
    proj_names = [p["name"] for p in hamza_projs]
    assert "UrbanCart Website" in proj_names and "QuickServe Mobile App" in proj_names
    
    hamza_tasks = get_user_tasks_summary(hamza)
    assert len(hamza_tasks) == 2, f"Hamza should have 2 tasks total, got {len(hamza_tasks)}"
    for t in hamza_tasks:
        assert t["assigneeId"] == "DEV02"
    print("✓ Agent Hamza multi-project isolation verified (sees UrbanCart & QuickServe, only his 2 tasks).")

    # 6. Modified Transcript Dynamic Adaptation Test
    print("\n[TEST 6] Testing Modified Transcript (QuickServe integration 12h, 23 Oct)...")
    mod_transcript_path = ROOT_DIR / "sample_data" / "modified_transcript.txt"
    mod_transcript_text = mod_transcript_path.read_text(encoding="utf-8")
    mod_draft = extract_projects_from_transcript(mod_transcript_text)
    
    # Check that QuickServe integration has 12 hours and 2026-10-23
    qs_mod = next(p for p in mod_draft["projects"] if "QuickServe" in p["name"])
    integ_task = next(t for t in qs_mod["tasks"] if "Mobile integration and testing" in t["title"])
    assert integ_task["estimatedHours"] == 12.0, f"Expected 12 hours, got {integ_task['estimatedHours']}"
    assert integ_task["deadline"] == "2026-10-23", f"Expected 2026-10-23, got {integ_task['deadline']}"
    print("✓ Dynamic AI transcript extraction verified for modified inputs.")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! (100% COMPLIANT)")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
