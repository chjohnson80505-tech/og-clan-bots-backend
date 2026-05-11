import os
import uuid
import time
import requests
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
import stripe

app = Flask(__name__)
CORS(app)

# ---------- CONFIG ----------
DISCORD_TOKEN   = os.getenv("DISCORD_TOKEN")
DISCORD_SERVER  = os.getenv("DISCORD_SERVER_ID")
OWNER_USER_ID   = "1362029045499432960" 
STRIPE_SECRET   = os.getenv("STRIPE_SECRET_KEY")

stripe.api_key = STRIPE_SECRET

# ---------- HELPERS ----------
def generate_timed_key(days=1):
    """Creates a key that embeds the expiration timestamp."""
    expire_time = int(time.time()) + (int(days) * 86400)
    return f"{uuid.uuid4()}-{expire_time}-OGCLAN"

# ---------- ROUTES ----------

@app.route("/")
def home():
    return "OG Clan Backend is Live!"

# THE REMOTE CONTROL & VERIFICATION
@app.route("/api/verify-key", methods=["POST", "GET"])
@app.route("/api/verify", methods=["POST", "GET"])
@app.route("/api/login", methods=["POST", "GET"])
@app.route("/api/redeem", methods=["POST", "GET"])
def verify_key():
    # Grabs data from everywhere (JSON, URL, Form)
    data = request.json or {}
    args = request.args or {}
    form = request.form or {}
    raw  = request.get_data(as_text=True) or ""

    full_search = f"{data} {args} {form} {raw}"
    print(f"DEBUG: IPA Sent: {full_search}") 

    try:
        # Finds the 10-digit timestamp in the key
        match = re.search(r'(\d{10})', full_search)
        
        if match:
            expiration_ts = int(match.group(1))
            current_ts = int(time.time())

            if current_ts < expiration_ts:
                # Returns EVERY success signal a modded IPA might look for
                return jsonify({
                    "valid": True,
                    "success": True,
                    "status": "success",
                    "ok": True,
                    "timeLeft": f"{(expiration_ts - current_ts) // 86400} days"
                })
        
        return jsonify({"valid": False, "success": False, "msg": "Expired or Invalid"})
    except Exception as e:
        return jsonify({"valid": False, "msg": str(e)})

@app.route("/api/key", methods=["POST"])
def api_key():
    data = request.json
    mode = data.get("mode")

    if mode == "redeem":
        code = data.get("code", "").strip()
        discord_id = str(data.get("discord_id", ""))

        # ADMIN 12-MONTH BYPASS
        if code == "ADMINKARMAYEARPASS" and discord_id == OWNER_USER_ID:
            return jsonify({"ok": True, "key": generate_timed_key(365)})
        
        return jsonify({"ok": False, "msg": "Invalid code or ID."})

    if mode == "purchase":
        amount = int(data.get("amount", 0))
        days = 1
        if amount == 500: days = 1
        elif amount == 2000: days = 7
        elif amount == 3500: days = 30
        elif amount == 7000: days = 180
        elif amount == 15000: days = 365
        return jsonify({"ok": True, "key": generate_timed_key(days)})

    return jsonify({"ok": False, "msg": "Bad request."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
