from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.api.v1.routes_saas import _create_or_get_supabase_user
from app.db.session import db_session


def main() -> None:
    email = os.getenv("SEED_SUPER_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("SEED_SUPER_ADMIN_PASSWORD", "")
    full_name = os.getenv("SEED_SUPER_ADMIN_NAME", "MedVoice Super Admin").strip() or "MedVoice Super Admin"
    if not email or not password:
        raise SystemExit("Set SEED_SUPER_ADMIN_EMAIL and SEED_SUPER_ADMIN_PASSWORD before running this command.")

    supabase_user_id = _create_or_get_supabase_user(email, password, full_name)
    with db_session() as db:
        row = db.execute(
            text(
                """
                INSERT INTO staff_users (hospital_id, supabase_user_id, email, full_name, role, status)
                VALUES (NULL, :supabase_user_id, :email, :full_name, 'super_admin', 'active')
                ON CONFLICT (supabase_user_id) DO UPDATE
                  SET hospital_id=NULL,
                      email=excluded.email,
                      full_name=excluded.full_name,
                      role='super_admin',
                      status='active',
                      updated_at=now()
                RETURNING id, email, full_name, role, status
                """
            ),
            {"supabase_user_id": supabase_user_id, "email": email, "full_name": full_name},
        ).mappings().one()
    print(f"Super admin ready: {row['email']} ({row['role']}, {row['status']})")


if __name__ == "__main__":
    main()
