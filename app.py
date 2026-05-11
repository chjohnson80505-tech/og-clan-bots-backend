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
OWNER_USER_ID   = "1362029045499432960" # Hardcoded for safety
STRIPE_SECRET   = os.getenv("STRIPE_SECRET_KEY")

stripe.api_key = STRIPE_SECRET

# ---------- HELPERS ----------
def generate_timed_key(days=1):
    """Creates a key with a clear timestamp."""
    expire_time = int(time.time()) + (int(days) * 86400)
    return f"{uuid.uuid4()}-{expire_time}-OGCLAN"

# ---------- ROUTES ----------

@app.route("/")
def home():
    return "OG Clan Backend is Live!"

# ALIASES: Catches /api/verify, /api/login, or /api/verify-key
@app.route("/api/verify-key", methods=["POST", "GET"])
@app.route("/api/verify", methods=["POST", "GET"])
@app.route("/api/login", methods=["POST", "GET"])
def verify_key():
    # Catch key from JSON body, URL parameters, or simple Form data
    data = request.json or {}
    key = data.get("key") or request.args.get("key") or request.form.get("key") or ""
    
    print(f"Checking Key: {key}") # This will show in your Render logs

    try:
        # Regex finds the 10-digit timestamp number inside the key
        match = re.search(r'-(\d{10})-OGCLAN', key)
        if not match:
            return jsonify({"valid": False, "msg": "Invalid key format."})
            
        expiration_ts = int(match.group(1))
        current_ts = int(time.time())

        if current_ts < expiration_ts:
            return jsonify({
                "valid": True, 
                "msg": "Key is active!",
                "timeLeft": f"{(expiration_ts - current_ts) // 86400} days"
            })
        else:
            return jsonify({"valid": False, "msg": "Key has expired."})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"valid": False, "msg": "Verification error."})

@app.route("/api/key", methods=["POST"])
def api_key():
    data = request.json
    mode = data.get("mode")

    if mode == "redeem":
        code = data.get("code", "").strip()
        discord_id = str(data.get("discord_id", ""))

        if code == "ADMINKARMAYEARPASS" and discord_id == OWNER_USER_ID:
            return jsonify({"ok": True, "key": generate_timed_key(365)})
        
        return jsonify({"ok": False, "msg": "Invalid code or unauthorized ID."})

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
