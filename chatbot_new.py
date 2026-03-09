from workers import WorkerEntrypoint, Response, fetch
import json
from urllib.parse import urlparse, parse_qs
import message_handler

# --- CONFIGURATION ---
PAGE_ACCESS_TOKEN = "EAAODzm1AH0IBO8LnrwlLOjr5VL5zAofXPEFp7S262pGlMaUEgupV6wleVdPDPQAk13YZALvGeznfWqz4kSkPbbwKENbn1EwPTpRevDNbgoZBjU6tPOZABS7RLKcWZBD5HrLe8VX1KrldBOibXGFWuk2PEfQGDj56zYFbzLKsFvdtJTP7Io7JCOd2iyZBOJ0ywoe6asbdt"
VERIFY_TOKEN = "939"

class MessengerAPI:
    """Helper class to send messages to Facebook Graph API"""
    @staticmethod
    async def send_message(recipient_id, text, quick_replies=None):
        url = f"https://graph.facebook.com/v22.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }
        if quick_replies:
            payload["message"]["quick_replies"] = quick_replies
            
        await fetch(
            url,
            method="POST",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = urlparse(request.url)
        
        # 1. FB WEBHOOK VERIFICATION
        if request.method == "GET":
            params = parse_qs(url.query)
            if params.get("hub.verify_token", [""])[0] == VERIFY_TOKEN:
                return Response(params.get("hub.challenge", [""])[0])
            return Response("Forbidden", status=403)

        # 2. MESSAGE PROCESSING
        if request.method == "POST":
            data = await request.json()
            # Fire-and-forget background task
            self.ctx.wait_until(self.handle_event(data))
            return Response("EVENT_RECEIVED", status=200)

    async def handle_event(self, data):
        """Extracts data and triggers our MessageHandler"""
        try:
            if data.get("object") == "page":
                for entry in data.get("entry", []):
                    for event in entry.get("messaging", []):
                        if "message" not in event or event["message"].get("is_echo"):
                            continue
                        
                        sender_id = event["sender"]["id"]
                        msg_text = event["message"].get("text", "")
                        qr_payload = event["message"].get("quick_reply", {}).get("payload")

                        # Initialize and run your separate logic file
                        handler = message_handler.MessageHandler(sender_id, self.env, MessengerAPI)
                        await handler.process_message(msg_text, qr_payload)

        except Exception as e:
            print(f"Worker Error: {e}")
