"""Reload a tenant portfolio from Initiative_Portfolio_Anonymised.xlsx.

Usage:
  uv run python scripts/load_portfolio_workbook.py --tenant-id <uuid> \
    --user-id <uuid> --workbook ../../Initiative_Portfolio_Anonymised.xlsx --confirm-reset
"""

from __future__ import annotations

import argparse
from pathlib import Path
from uuid import UUID

from app.core.database import get_supabase_admin
from app.services.portfolio_workbook import PortfolioWorkbookReloadService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--user-id")
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--no-reset", action="store_true")
    parser.add_argument("--confirm-reset", action="store_true")
    parser.add_argument("--parse-only", action="store_true")
    args = parser.parse_args()

    if not args.parse_only and not args.no_reset and not args.confirm_reset:
        parser.error("--confirm-reset is required unless --no-reset or --parse-only is used")

    workbook_path = Path(args.workbook).expanduser().resolve()
    data = workbook_path.read_bytes()
    service = PortfolioWorkbookReloadService(
        get_supabase_admin(),
        UUID(args.tenant_id),
        UUID(args.user_id) if args.user_id else None,
    )
    if args.parse_only:
        parsed = service.parse(data)
        print({"initiatives": len(parsed)})
        return
    print(service.reload(data, reset=not args.no_reset))


if __name__ == "__main__":
    main()
