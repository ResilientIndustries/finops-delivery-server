import os
from flask import Flask, request, jsonify
import stripe
import resend

app = Flask(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
resend.api_key = os.getenv("RESEND_API_KEY")

@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature")

    try:
        if endpoint_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        else:
            event = json.loads(payload)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_details", {}).get("email")

        print(f"\n💰 Payment confirmed from {customer_email}! Dispatching asset...")

        try:
            with open("generated_blueprint.md", "r", encoding="utf-8") as f:
                blueprint_content = f.read()
        except Exception:
            blueprint_content = "Thank you for your purchase! Your blueprint download package."

        if customer_email and resend.api_key:
            try:
                resend.Emails.send({
                    "from": "FinOps Blueprints <sales@resilientindustries.io>",
                    "to": customer_email,
                    "subject": "Your $49 FinOps Architecture Blueprint & Code Package",
                    "text": f"Thank you for your purchase!\n\n{blueprint_content}"
                })
                print(f"✅ Asset email sent to {customer_email}")
            except Exception as e:
                print(f"❌ Resend error: {e}")

    return jsonify({"status": "success"}), 200

@app.route("/", methods=["GET"])
def health_check():
    return "FinOps Delivery Engine Online", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4242))
    app.run(host="0.0.0.0", port=port)