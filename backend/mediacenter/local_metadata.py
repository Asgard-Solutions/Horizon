"""Display metadata supplied by local NFO files. No network provider or automatic writes."""
import json

TABLES = {"movie": "movies", "tv": "shows", "episode": "episodes"}


def parsed(value, fallback=None):
    try:
        return json.loads(value) if value else fallback
    except (TypeError, ValueError):
        return fallback


def record_local(conn, kind, row_id, base, overrides, extras):
    conn.execute(f"UPDATE {TABLES[kind]} SET local_metadata=? WHERE id=?",
                 (json.dumps({"base": base, "overrides": list(overrides), "extras": extras}), row_id))


def apply_local(conn, kind, row_id):
    row = conn.execute(f"SELECT local_metadata FROM {TABLES[kind]} WHERE id=?", (row_id,)).fetchone()
    values = parsed(row[0], {}).get("base", {}) if row else {}
    allowed = {"title", "sort_title", "year", "plot", "poster_path", "fanart_path", "genres", "thumb_path"}
    values = {key: value for key, value in values.items() if key in allowed}
    if "title" in values and kind != "episode" and "sort_title" not in values:
        from .parser import sort_key
        values["sort_title"] = sort_key(values["title"])
    if values:
        conn.execute(f"UPDATE {TABLES[kind]} SET " + ",".join(f"{k}=?" for k in values) + " WHERE id=?", (*values.values(), row_id))


def public_details(row):
    local = parsed(row["local_metadata"], {}) if "local_metadata" in row.keys() else {}
    extras = local.get("extras", {})
    return {"cast": extras.get("cast", []), "rating": extras.get("rating"), "premiered": extras.get("premiered"), "tagline": extras.get("tagline"),
            "external_ids": extras.get("ids", {})}
