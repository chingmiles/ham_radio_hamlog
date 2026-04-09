This patch is based on the current public repository baseline (README identifies it as HamLog Prototype v2.5).

Files included:
- app/app.py
- app/dxcc.json
- app/templates/qso_form.html
- app/templates/qso_list.html
- app/templates/public_qso_list.html

How to apply:
1. Back up your current repo.
2. Overwrite the files in the same paths.
3. Rebuild with: docker compose down && docker compose build --no-cache && docker compose up -d

What changes:
- Replaces the small hard-coded DXCC prefix list with a full DXCC dataset loaded from app/dxcc.json.
- Uses regex + longest-prefix scoring for more complete callsign-to-DXCC matching.
- Adds ADIF/CQ/ITU/continent/ISO aware lookup.
- Keeps existing page layout untouched.
- Uses local flags if present, otherwise falls back to flagcdn by ISO code, and finally a generated badge.
- Replaces the client-side preview map with a lightweight /api/dxcc-lookup endpoint.
