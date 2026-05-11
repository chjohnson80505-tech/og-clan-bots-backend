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
OWNER_USER_ID   = os.getenv("OWNER_USER_ID")
STRIPE_SECRET   = os.getenv("STRIPE_SECRET_KEY")

stripe.api_key = STRIPE_SECRET

# ---------- HELPERS ----------
def generate_timed_key(days=1):
    """Creates a key that embeds the expiration timestamp."""
    expire_time = int(time.time()) + (days * 86400)
    return f"{uuid.uuid4()}-{expire_time}-OGCLAN"

def discord_has_role(user_id, role_name="ogclanmember"):
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

# This is what Shark IPA calls to check if the key is still valid
@app.route("/api/verify-key", methods=["POST"])
def verify_key():
    data = request.json
    key = data.get("key", "")
    try:
        parts = key.split("-")
        expiration_ts = int(parts[-2]) # Get the timestamp from the key
        if int(time.time()) < expiration_ts:
            return jsonify({"valid": True, "msg": "Key is active!"})
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
        discord_id = data.get("discord_id")

        if code == "OGCLANONEDAYPASS":
            if not discord_has_role(discord_id):
                return jsonify({"ok": False, "msg": "You must have the ogclanmember role."})
            return jsonify({"ok": True, "key": generate_timed_key(1)})

        if code == "ADMINKARMAYEARPASS":
            if discord_id != OWNER_USER_ID:
                return jsonify({"ok": False, "msg": "Only the server owner can use this."})
            return jsonify({"ok": True, "key": generate_timed_key(365)})

        return jsonify({"ok": False, "msg": "Invalid code."})

    if mode == "purchase":
        amount = int(data.get("amount", 0))
        source = data.get("source")
        try:
            charge = stripe.Charge.create(
                amount=amount, currency="usd", source=source, description="OG Clan Bot Pass"
            )
            if charge["paid"]:
                # Logic for different time lengths based on price in cents
                days = 1
                if amount == 2000: days = 7
                elif amount == 3500: days = 30
                elif amount == 7000: days = 180
                elif amount == 15000: days = 365
                
                return jsonify({"ok": True, "key": generate_timed_key(days)})
        except stripe.error.StripeError as e:
            return jsonify({"ok": False, "msg": str(e)})

    return jsonify({"ok": False, "msg": "Bad request."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
