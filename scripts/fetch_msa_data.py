"""Download ACS B07201 for every US metro area via Census Reporter."""

from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "msa-data.json"
GAZ_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2024_Gazetteer/2024_Gaz_cbsa_national.zip"
)
UA = {"User-Agent": "pgh-msa-movers/1.0 (personal research)"}
COLS = {
    "total": "B07201001",
    "sameHouse": "B07201002",
    "usMove": "B07201003",
    "sameMsa": "B07201004",
    "fromCity": "B07201005",
    "fromRemainder": "B07201006",
    "otherMetro": "B07201007",
    "micro": "B07201010",
    "nonMetro": "B07201013",
    "abroad": "B07201014",
}


def get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def metro_list() -> list[dict]:
    raw = get(GAZ_URL)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        text = zf.read(zf.namelist()[0]).decode("latin-1")
    metros = []
    for line in text.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        geoid, name, cbsa_type = parts[1].strip(), parts[2].strip(), parts[3].strip()
        if cbsa_type != "1":
            continue
        short = name.removesuffix(" Metro Area")
        metros.append({"id": geoid, "name": short, "fullName": name})
    metros.sort(key=lambda m: m["name"])
    return metros


def fetch_one(metro: dict, retries: int = 6) -> dict | None:
    geoid = f"31000US{metro['id']}"
    url = (
        "https://api.censusreporter.org/1.0/data/show/latest"
        f"?table_ids=B07201&geo_ids={geoid}"
    )
    for attempt in range(retries):
        try:
            payload = json.loads(get(url, timeout=45))
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                wait = 2 ** attempt
                print(f"429 {metro['name']}; wait {wait}s", flush=True)
                time.sleep(wait)
                continue
            print(f"skip {metro['id']} {metro['name']}: HTTP {exc.code}")
            return None
        except Exception as exc:
            print(f"skip {metro['id']} {metro['name']}: {exc}")
            return None
    else:
        return None
    block = payload.get("data", {}).get(geoid, {}).get("B07201", {})
    est = block.get("estimate") or {}
    err = block.get("error") or {}
    vals = {}
    for key, col in COLS.items():
        n = est.get(col)
        if n is None:
            print(f"skip {metro['id']} {metro['name']}: missing {col}")
            return None
        vals[key] = int(round(n))
        moe = err.get(col)
        vals[key + "Moe"] = int(round(moe)) if moe is not None else None
    movers = vals["usMove"] + vals["abroad"]
    if movers <= 0:
        return None
    intra = 100.0 * vals["sameMsa"] / movers
    release = payload.get("release", {})
    return {
        **metro,
        **vals,
        "movers": movers,
        "inbound": movers - vals["sameMsa"],
        "intraShare": round(intra, 1),
        "release": release.get("id", "acs2024_1yr"),
    }


def main() -> None:
    metros = metro_list()
    print(f"{len(metros)} metro areas", flush=True)
    existing: dict[str, dict] = {}
    if OUT.exists():
        prior = json.loads(OUT.read_text(encoding="utf-8"))
        existing = {m["id"]: m for m in prior.get("metros", [])}
        print(f"loaded {len(existing)} cached metros")
    missing = [m for m in metros if m["id"] not in existing]
    print(f"{len(missing)} still to fetch")
    results = list(existing.values())
    for i, metro in enumerate(missing, 1):
        row = fetch_one(metro)
        if row:
            results.append(row)
        if i % 10 == 0 or i == len(missing):
            print(f"  {i}/{len(missing)}  kept {len(results)}", flush=True)
            results.sort(key=lambda r: r["name"])
            payload = {
                "source": "U.S. Census Bureau, ACS 2024 1-year, table B07201",
                "via": "Census Reporter",
                "universe": "Population 1 year and over living in a Metropolitan Statistical Area",
                "count": len(results),
                "metros": results,
            }
            OUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        time.sleep(0.5)
    results.sort(key=lambda r: r["name"])
    payload = {
        "source": "U.S. Census Bureau, ACS 2024 1-year, table B07201",
        "via": "Census Reporter",
        "universe": "Population 1 year and over living in a Metropolitan Statistical Area",
        "count": len(results),
        "metros": results,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes, {len(results)} metros)")


if __name__ == "__main__":
    main()
