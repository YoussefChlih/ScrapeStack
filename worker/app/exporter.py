"""
Export generator — produces JSON, CSV, and XLSX files from scraped data
and uploads them to Supabase Storage.
"""

import io
import json
import logging
from datetime import datetime, timezone

import pandas as pd
from app.supabase_client import get_supabase

logger = logging.getLogger("scrapestack.exporter")


def build_dataframe(job_id: str) -> pd.DataFrame:
    """Build a pandas DataFrame from scraped pages data."""
    sb = get_supabase()
    
    pages_resp = (
        sb.table("scraped_pages")
        .select("*")
        .eq("job_id", job_id)
        .order("scraped_at")
        .execute()
    )
    
    if not pages_resp.data:
        return pd.DataFrame()

    rows = []
    for page in pages_resp.data:
        rows.append({
            "URL": page["url"],
            "Title": page.get("title", ""),
            "Meta Description": page.get("meta_description", ""),
            "Status Code": page.get("status_code", 0),
            "Word Count": page.get("word_count", 0),
            "Links Found": page.get("links_found", 0),
            "Scraped At": page.get("scraped_at", ""),
        })

    return pd.DataFrame(rows)


async def generate_exports(job_id: str):
    """Generate JSON, CSV, and XLSX exports and upload to Supabase Storage."""
    sb = get_supabase()
    
    # Fetch job to get user_id
    job_resp = sb.table("scrape_jobs").select("user_id").eq("id", job_id).single().execute()
    user_id = job_resp.data["user_id"]

    df = build_dataframe(job_id)
    if df.empty:
        logger.warning(f"No data to export for job {job_id}")
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bucket = "exports"

    # Ensure bucket exists (ignore error if it already does)
    try:
        sb.storage.create_bucket(id=bucket, name=bucket, options={"public": False})
    except Exception:
        pass

    exports = []

    # --- JSON ---
    json_data = df.to_json(orient="records", indent=2)
    json_bytes = json_data.encode("utf-8")
    json_path = f"{user_id}/{job_id}/export_{timestamp}.json"
    
    sb.storage.from_(bucket).upload(
        json_path,
        json_bytes,
        {"content-type": "application/json"},
    )
    json_url = sb.storage.from_(bucket).create_signed_url(json_path, 60 * 60 * 24 * 7)  # 7 days
    exports.append({
        "job_id": job_id,
        "user_id": user_id,
        "format": "json",
        "file_url": json_url.get("signedURL", json_url.get("signedUrl", "")),
    })

    # --- CSV ---
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue().encode("utf-8")
    csv_path = f"{user_id}/{job_id}/export_{timestamp}.csv"
    
    sb.storage.from_(bucket).upload(
        csv_path,
        csv_bytes,
        {"content-type": "text/csv"},
    )
    csv_url = sb.storage.from_(bucket).create_signed_url(csv_path, 60 * 60 * 24 * 7)
    exports.append({
        "job_id": job_id,
        "user_id": user_id,
        "format": "csv",
        "file_url": csv_url.get("signedURL", csv_url.get("signedUrl", "")),
    })

    # --- XLSX ---
    xlsx_buffer = io.BytesIO()
    df.to_excel(xlsx_buffer, index=False, engine="openpyxl")
    xlsx_bytes = xlsx_buffer.getvalue()
    xlsx_path = f"{user_id}/{job_id}/export_{timestamp}.xlsx"
    
    sb.storage.from_(bucket).upload(
        xlsx_path,
        xlsx_bytes,
        {"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    )
    xlsx_url = sb.storage.from_(bucket).create_signed_url(xlsx_path, 60 * 60 * 24 * 7)
    exports.append({
        "job_id": job_id,
        "user_id": user_id,
        "format": "xlsx",
        "file_url": xlsx_url.get("signedURL", xlsx_url.get("signedUrl", "")),
    })

    # Insert export records
    if exports:
        sb.table("exports").insert(exports).execute()
        logger.info(f"Created {len(exports)} export records for job {job_id}")
