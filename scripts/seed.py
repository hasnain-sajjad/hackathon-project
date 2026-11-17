import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.database import init_db
from app.auth import seed_demo_users

def main():
    print("==================================================")
    print("NovaWorks Technologies - Demo Accounts Seeder")
    print("==================================================")
    init_db()
    count = seed_demo_users()
    print(f"Successfully configured and seeded {count} demo accounts.")
    print("Sample Password for all accounts: Demo123!")
    print("==================================================")

if __name__ == "__main__":
    main()
