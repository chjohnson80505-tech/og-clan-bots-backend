import os
import uuid
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import stripe

app = Flask(__name__)
CORS(app)

# ---------- CONFIG ----------
DISCORD_TOKEN   = os.getenv("DISCORD_TOKEN")
DISCORD_SERVER  = os.getenv("DISCORD_SERVER_ID")
OWNER_USER_ID   = "1362029045499432960" # Hardcoded for safety
STRIPE_SECRET   = os.getenv("STRIPE_SECRET_KEY")

stripe.api_key = STRIPE_SECRET

# ---------- HELPERS ----------
def generate_timed_key(days=1):
    """Creates a key that embeds the expiration timestamp."""
    expire_time = int(time.time()) + (int(days) * 86400)
    return f"{uuid.uuid4()}-{expire_time}-OGCLAN"

def discord_has_role(user_id, role_name="ogclanmember"):
    # Fixed Discord API URL paths
    url = f"https://discord.com{DISCORD_SERVER}/members/{user_id}"
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200: return False
    
    member = r.json()
    role_url = f"https://discord.com{DISCORD_SERVER}/roles"
    rr = requests.get(role_url, headers=headers)
    
    role_id = None
    if rr.status_code == 200:
        for r_obj in rr.json():
            if r_obj["name"].lower() == role_name.lower():
                role_id = r_obj["id"]
                break
    return role_id in member.get("roles", []) if role_id else False

# ---------- ROUTES ----------

@app.route("/")
def home():
    return "OG Clan Backend is Live!"

@app.route("/api/verify-key", methods=["POST"])
def verify_key():
    data = request.json
    key = data.get("key", "")
    try:
        parts = key.split("-")
        expiration_ts = int(parts[-2]) 
        if int(time.time()) < expiration_ts:
            return jsonify({"valid": True, "msg": "Key is active!", "timeLeft": f"{(expiration_ts - int(time.time())) // 3600} hours"})
        else:
            return jsonify({"valid": False, "msg": "Key has expired."})
    except:
        return jsonify({"valid": False, "msg": "Invalid key format."})

@app.route("/api/key", methods=["POST"])
def api_key():
    data = request.json
    mode = data.get("mode")

    if mode == "redeem":
        code = data.get("code", "").strip()
        discord_id = str(data.get("discord_id", ""))

        # ADMIN YEAR PASS CHECK
        if code == "ADMINKARMAYEARPASS":
            if discord_id == OWNER_USER_ID:
                return jsonify({"ok": True, "key": generate_timed_key(365)})
            else:
                return jsonify({"ok": False, "msg": "Unauthorized Discord ID."})

        # STANDARD ONE DAY PASS
        if code == "OGCLANONEDAYPASS":
            if not discord_has_role(discord_id):
                return jsonify({"ok": False, "msg": "Missing Discord Role."})
            return jsonify({"ok": True, "key": generate_timed_key(1)})

        return jsonify({"ok": False, "msg": "Invalid code."})

    if mode == "purchase":
        # amount is sent in cents from frontend
        amount = int(data.get("amount", 0))
        try:
            # Map cents to days based on your frontend prices
            days = 1 # default
            if amount == 500: days = 1
            elif amount == 2000: days = 7
            elif amount == 3500: days = 30
            elif amount == 7000: days = 180
            elif amount == 15000: days = 365
            
            return jsonify({"ok": True, "key": generate_timed_key(days)})
        except Exception as e:
            return jsonify({"ok": False, "msg": "Error generating purchase key."})

    return jsonify({"ok": False, "msg": "Bad request."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
