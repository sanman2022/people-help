"""
Seed script for People Help demo.

Usage:  python db/seed.py          (server must be running at http://127.0.0.1:8000)
  npm run seed                     (same thing, from package.json)

What it does:
  1. Truncates ALL data tables (clean slate)
  2. Seeds knowledge base docs (calls /knowledge/seed — requires OpenAI for embeddings)
  3. Seeds workflow definitions (onboarding, pto_request, expense_reimbursement)
  4. Seeds connectors (Workday, Greenhouse, Slack, Okta)
  5. Creates demo cases, onboarding runs, approvals, events, and feedback
"""

import os
import sys
import time

import httpx

BASE = os.environ.get("SEED_BASE_URL", "http://127.0.0.1:8000")
CLIENT = httpx.Client(timeout=120, follow_redirects=True)


# ---------------------------------------------------------------------------
# 1. Clean all tables
# ---------------------------------------------------------------------------

def clean_tables():
    """Truncate all data tables via a dedicated endpoint."""
    print("[1/5] Cleaning all tables...")
    r = CLIENT.post(f"{BASE}/seed/reset")
    if r.status_code != 200:
        print(f"  ERROR: /seed/reset returned {r.status_code}: {r.text[:200]}")
        sys.exit(1)
    data = r.json()
    print(f"  Cleaned {data.get('tables_cleaned', '?')} tables")


# ---------------------------------------------------------------------------
# 2. Seed knowledge base
# ---------------------------------------------------------------------------

def seed_knowledge():
    """Ingest demo policy docs (PTO, expenses, onboarding, hiring, etc.)."""
    print("[2/5] Seeding knowledge base (generating embeddings — may take 30s)...")
    r = CLIENT.post(f"{BASE}/knowledge/seed")
    if r.status_code != 200:
        print(f"  ERROR: /knowledge/seed returned {r.status_code}: {r.text[:200]}")
        return
    data = r.json()
    print(f"  Ingested {data.get('ingested', '?')} documents")


# ---------------------------------------------------------------------------
# 3. Seed workflow definitions
# ---------------------------------------------------------------------------

def seed_definitions():
    """Seed default workflow definitions."""
    print("[3/5] Seeding workflow definitions...")
    r = CLIENT.post(f"{BASE}/workflows/definitions/seed")
    if r.status_code != 200:
        print(f"  ERROR: returned {r.status_code}: {r.text[:200]}")
        return
    data = r.json()
    print(f"  Seeded {data.get('seeded', '?')} definitions")


# ---------------------------------------------------------------------------
# 4. Seed connectors
# ---------------------------------------------------------------------------

def seed_connectors():
    """Seed connector health records."""
    print("[4/5] Seeding connectors...")
    r = CLIENT.post(f"{BASE}/seed/connectors")
    if r.status_code != 200:
        print(f"  ERROR: returned {r.status_code}: {r.text[:200]}")
        return
    data = r.json()
    print(f"  Seeded {data.get('count', '?')} connectors")


# ---------------------------------------------------------------------------
# 5. Seed demo data (cases, onboarding, events, feedback)
# ---------------------------------------------------------------------------

def seed_demo_data():
    """Create realistic demo cases, onboarding runs, and events."""
    print("[5/5] Seeding demo data (cases, onboarding runs, events, feedback)...")
    r = CLIENT.post(f"{BASE}/seed/demo-data")
    if r.status_code != 200:
        print(f"  ERROR: returned {r.status_code}: {r.text[:200]}")
        return
    data = r.json()
    print(f"  Created: {data.get('cases', 0)} cases, "
          f"{data.get('onboarding_runs', 0)} onboarding runs, "
          f"{data.get('events', 0)} events, "
          f"{data.get('feedback', 0)} feedback entries")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("People Help — Seed Demo Data")
    print("=" * 60)
    print()

    # Quick health check
    try:
        r = CLIENT.get(f"{BASE}/health")
        if r.status_code != 200:
            raise Exception(f"Health check returned {r.status_code}")
    except Exception as e:
        print(f"ERROR: Server not reachable at {BASE}")
        print(f"  Make sure the server is running: npm start")
        print(f"  ({e})")
        sys.exit(1)

    clean_tables()
    seed_knowledge()
    seed_definitions()
    seed_connectors()
    seed_demo_data()

    print()
    print("=" * 60)
    print("Done! Visit http://127.0.0.1:8000 to explore the demo.")
    print("=" * 60)


if __name__ == "__main__":
    main()
