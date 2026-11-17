import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.database import init_db
from app.auth import seed_demo_users
from app.ai_extractor import (
    get_directory_summary,
    extract_projects_from_transcript,
    validate_extracted_data
)

def test_modified_transcript():
    print("==================================================")
    print("TEST: Dynamic AI Extraction on Modified Transcript")
    print("==================================================")
    init_db()
    seed_demo_users()
    
    transcript_path = ROOT_DIR / "sample_data" / "modified_transcript.txt"
    transcript_text = transcript_path.read_text(encoding="utf-8")
    
    directory = get_directory_summary()
    draft = extract_projects_from_transcript(transcript_text)
    
    errors = validate_extracted_data(draft, directory)
    assert not errors, f"Validation errors: {errors}"
    
    # Locate QuickServe Mobile App
    qs = next((p for p in draft["projects"] if "QuickServe" in p["name"]), None)
    assert qs is not None, "QuickServe project not found"
    
    # Locate Mobile integration and testing
    integ = next((t for t in qs["tasks"] if "Mobile integration and testing" in t["title"]), None)
    assert integ is not None, "Mobile integration task not found"
    
    print(f"Project: {qs['name']}")
    print(f"Task: {integ['title']}")
    print(f"Assignee: {integ['assigneeId']} (Usman)")
    print(f"Deadline: {integ['deadline']} (Expected: 2026-10-23)")
    print(f"Estimated Hours: {integ['estimatedHours']} (Expected: 12)")
    
    assert integ["estimatedHours"] == 12.0, f"Expected 12 hours, got {integ['estimatedHours']}"
    assert integ["deadline"] == "2026-10-23", f"Expected 2026-10-23, got {integ['deadline']}"
    
    # Verify other tasks unchanged
    login_screen = next((t for t in qs["tasks"] if "Login and profile screens" in t["title"]), None)
    assert login_screen["estimatedHours"] == 8.0
    assert login_screen["deadline"] == "2026-10-12"
    
    print("\n✓ PASSED: Genuine dynamic conversion verified! Modified hours & deadline successfully extracted without affecting other tasks.")
    print("==================================================")

if __name__ == "__main__":
    test_modified_transcript()
