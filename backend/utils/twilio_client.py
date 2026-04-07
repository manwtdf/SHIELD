import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")
DEMO_ALERT_NUMBER = os.getenv("DEMO_ALERT_NUMBER")

def send_alert(to_number: str = None, score: int = 27, top_anomalies: list = []):
    """
    Send a Twilio SMS alert to the user.
    """
    if not to_number:
        to_number = DEMO_ALERT_NUMBER
        
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, to_number]):
        print("Twilio credentials or demo phone number missing. Logging alert instead.")
        print(f"ALERT: Score {score}, Anomalies: {', '.join(top_anomalies)}")
        return {"sent": False, "error": "Credentials missing"}

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        reason = ", ".join(top_anomalies[:3])
        message_body = (
            f"🚨 BehaviorShield Alert: Suspicious activity on your account.\n"
            f"Risk score: {score}/100. Reason: {reason}.\n"
            f"Your transaction has been frozen. Call 1800-XXX-XXXX to verify."
        )

        message = client.messages.create(
            body=message_body,
            from_=TWILIO_FROM_NUMBER,
            to=to_number
        )
        
        print(f"SMS Sent! SID: {message.sid}")
        return {"sent": True, "message_sid": message.sid}
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return {"sent": False, "error": str(e)}

if __name__ == "__main__":
    # Test send
    send_alert(score=27, top_anomalies=["Typing delay +80%", "New device", "SIM swap detected"])
