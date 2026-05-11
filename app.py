import os
import uuid
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import stripe

app = Flask(__name__)
CORS(app) # This is CRITICAL for your frontend to work

# ---------- CONFIG ----------
DISCORD_TOKEN   = os.getenv("DISCORD_TOKEN")
DISCORD_SERVER  = os.getenv("DISCORD_SERVER_ID")
OWNER_USER_ID   = os.getenv("OWNER_USER_ID")
STRIPE_SECRET   = os.getenv("STRIPE_SECRET_KEY")

stripe.api_key = STRIPE_SECRET

@app.route("/")
def home():
    return "Backend is Live!"

# ---------- HELPERS ----------
def discord_has_role(user_id, role_name="ogclanmember"):
    url = f"https://discord.com/api/v9/guilds/{DISCORD_SERVER}/members/{user_id}"
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return False
    member = r.json()
    role_url = f"https://discord.com/api/v9/guilds/{DISCORD_SERVER}/roles"
    rr = requests.get(role_url, headers=headers)
    role_id = None
    if rr.status_code == 200:
        for r_obj in rr.json():
            if r_obj["name"].lower() == role_name.lower():
                role_id = r_obj["id"]
                break
    if not role_id:
        return False
    return role_id in member.get("roles", [])

def generate_key():
    return f"{uuid.uuid4()}-OGCLAN"

# ---------- ROUTES ----------
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
            return jsonify({"ok": True, "key": generate_key(), "type": "daily"})
        if code == "ADMINKARMAYEARPASS":
            if discord_id != OWNER_USER_ID:
                return jsonify({"ok": False, "msg": "Only the server owner may use this code."})
            return jsonify({"ok": True, "key": generate_key(), "type": "yearly"})
        return jsonify({"ok": False, "msg": "Invalid redemption code."})

    if mode == "purchase":
        amount = int(data.get("amount", 0))
        source = data.get("source")
        try:
            charge = stripe.Charge.create(
                amount=amount, currency="usd", source=source, description="OG Clan Bot Pass"
            )
            if charge["paid"]:
                return jsonify({"ok": True, "key": generate_key()})
        except stripe.error.StripeError as e:
            return jsonify({"ok": False, "msg": str(e)})

    return jsonify({"ok": False, "msg": "Bad request."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
