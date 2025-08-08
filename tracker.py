import os, requests, json, time, pathlib

# --- Umgebungsvariablen (setzen wir gleich in GitHub) ---
ICAO = os.getenv("ICAO_HEX")             # z.B. ab12cd
ADSB_URL = os.getenv("ADSB_URL")         # z.B. https://.../api/aircraft/json/hex/ab12cd
TG_TOKEN = os.getenv("TG_TOKEN")         # Telegram Bot Token (Secret)
TG_CHAT  = os.getenv("TG_CHAT_ID")       # Chat-ID
MIN_GS   = int(os.getenv("MIN_GS", "40"))  # kts, ab hier gilt "in der Luft"

STATE = pathlib.Path("state.json")

def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "Markdown"})
    r.raise_for_status()

def load_state():
    if STATE.exists():
        with STATE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_flight": None, "airborne": False}

def save_state(s):
    with STATE.open("w", encoding="utf-8") as f:
        json.dump(s, f)

def main():
    r = requests.get(ADSB_URL, timeout=20)
    r.raise_for_status()
    data = r.json()

    # ADSBexchange-Format: Liste unter "ac"
    ac = data.get("ac") or []
    if not ac:
        print("Kein AC-Datensatz.")
        return
    jet = ac[0]

    alt = jet.get("alt_baro") or jet.get("geoaltitude") or 0
    gs  = jet.get("gs") or 0
    reg = jet.get("r") or jet.get("flight") or ICAO
    flight_id = (jet.get("flight") or f"{ICAO}-{int(time.time()//3600)}").strip()

    is_airborne = bool((alt and alt > 0) or (gs and gs >= MIN_GS))

    state = load_state()
    should_alert = is_airborne and (not state.get("airborne") or state.get("last_flight") != flight_id)

    if should_alert:
        msg = f"✈️ *{reg}* ({ICAO}) ist in der Luft – Alt: {int(alt)} ft, GS: {int(gs)} kts"
        send_telegram(msg)
        print("Alert gesendet.")

    state["airborne"] = is_airborne
    state["last_flight"] = flight_id
    save_state(state)

if __name__ == "__main__":
    main()
