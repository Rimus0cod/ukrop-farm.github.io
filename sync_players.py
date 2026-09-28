import json, re
from datetime import datetime, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
ROSTER = ROOT / "roster.js"
OUT = ROOT / "players.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UkropFarmPlayerSync/1.0)"}
RANKS = ["Herald","Guardian","Crusader","Archon","Legend","Ancient","Divine","Immortal"]

def get(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def value(block, key):
    m = re.search(rf"{key}:\s*['\"](.*?)['\"]", block)
    return m.group(1) if m else ""

def parse_roster():
    text = ROSTER.read_text(encoding="utf-8")
    blocks = re.findall(r"\{(.*?)\n\s*\}", text, re.S)
    out = []
    for block in blocks:
        steam = value(block, "steam")
        steam_id = value(block, "steamId")
        if not steam:
            continue
        out.append({
            "nick": value(block, "nick"),
            "name": value(block, "name"),
            "role": value(block, "role"),
            "roleRu": value(block, "roleRu"),
            "steam": steam,
            "steamId": steam_id,
            "active": not bool(re.search(r"active:\s*false", block)),
        })
    return out

def resolve_steam_id(player):
    if player["steamId"]:
        return player["steamId"]
    html = get(player["steam"])
    m = re.search(r"steamID64[^0-9]*(\d{17})", html, re.I)
    if not m:
        m = re.search(r"g_rgProfileData\s*=\s*\{.*?steamid['\"]\s*:\s*['\"](\d{17})", html, re.I | re.S)
    if not m:
        raise RuntimeError(f"Cannot resolve SteamID64: {player['steam']}")
    return m.group(1)

def parse_steam(player):
    result = {}
    html = get(player["steam"] if not player["steam"].startswith("https://steamcommunity.com/profiles/") else player["steam"] + "?l=english")
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"property": "og:image"})
    if meta and meta.get("content"):
        result["avatar"] = meta["content"]
    title = soup.find("title")
    if title:
        name = re.sub(r"\s*::\s*Steam Community.*$", "", title.get_text(" ", strip=True))
        if name:
            result["steamName"] = name
    return result

def steam32(steam64):
    return str(int(steam64) - 76561197960265728)

def parse_rank(text):
    m = re.search(r"\b(" + "|".join(RANKS) + r")(?:\s+([1-5]))?\b", " ".join(text.split()), re.I)
    if not m:
        return None
    return m.group(1).capitalize() + (f" {m.group(2)}" if m.group(2) else "")

def parse_dotabuff(steam_id):
    html = get(f"https://www.dotabuff.com/players/{steam32(steam_id)}")
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    result = {}
    rank = parse_rank(text)
    if rank:
        result["rank"] = rank
    heading = next((x for x in soup.find_all(["h2","h3","h4"]) if "Most Played Heroes" in x.get_text(" ", strip=True)), None)
    table = heading.find_next("table") if heading else None
    if table:
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td","th"])]
            if len(cells) >= 2 and cells[0].lower() not in {"hero","heroes"} and cells[0]:
                result["favoriteHero"] = cells[0]
                break
    return result

def main():
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"players":[]}
    old_by_id = {p.get("steamId"): p for p in old.get("players", []) if p.get("steamId")}
    players = []
    for p in parse_roster():
        try:
            sid = resolve_steam_id(p)
            p["steamId"] = sid
            previous = old_by_id.get(sid, {})
            merged = {**previous, **p}
            try:
                merged.update(parse_steam(p))
            except Exception as e:
                print("Steam:", sid, e)
            try:
                merged.update(parse_dotabuff(sid))
            except Exception as e:
                print("Dotabuff:", sid, e)
            merged["dotabuff"] = f"https://www.dotabuff.com/players/{steam32(sid)}"
            players.append(merged)
        except Exception as e:
            print("Player failed:", p.get("nick"), e)
            players.append({**old_by_id.get(p.get("steamId"), {}), **p})
    OUT.write_text(json.dumps({
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Steam + Dotabuff",
        "players": players
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
