import requests
import json

# Mock a Stripe checkout.session.completed payload
mock_payload = {
    "type": "checkout.session.completed",
    "data": {
        "object": {
            "customer_details": {
                "email": "brandon@resilientindustries.io" # Put your actual email here to test receipt
            }
        }
    }
}

headers = {"Content-Type": "application/json"}

print("🚀 Sending mock webhook event to local Flask server...")
response = requests.post("http://localhost:4242/webhook", data=json.dumps(mock_payload), headers=headers)

print(f"Response Status: {response.status_code}")
print(f"Response Body: {response.text}")