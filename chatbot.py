import os
import json
import requests
import responses
from flask import Flask, request

# Facebook API Credentials
ACCESS_TOKEN = "EAAODzm1AH0IBO8LnrwlLOjr5VL5zAofXPEFp7S262pGlMaUEgupV6wleVdPDPQAk13YZALvGeznfWqz4kSkPbbwKENbn1EwPTpRevDNbgoZBjU6tPOZABS7RLKcWZBD5HrLe8VX1KrldBOibXGFWuk2PEfQGDj56zYFbzLKsFvdtJTP7Io7JCOd2iyZBOJ0ywoe6asbdt"
VERIFY_TOKEN = "939"

# Global dictionary to store session data for each user.
# Each entry will be a dictionary, e.g.: { "language": "english_language_", "ended": False, "welcome_sent": False }
user_sessions = {}  

# Create Flask App (Global)
app = Flask(__name__)

@app.route("/")
def home():
    return "Chatbot is running!"  # Message to show when accessing the root URL

class MessengerAPI:
    """Handles sending messages to Facebook Messenger API"""
    BASE_URL = "https://graph.facebook.com/v21.0/me/messages"  # Updated to latest API

    @staticmethod
    def send_message(recipient_id, text, quick_replies=None):
        headers = {"Content-Type": "application/json"}
        data = {
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }
        if quick_replies:
            data["message"]["quick_replies"] = quick_replies
        response = requests.post(
            MessengerAPI.BASE_URL,
            params={"access_token": ACCESS_TOKEN},
            headers=headers,
            json=data
        )
        print(f"Sent message response: {response.status_code}, {response.text}")  # Debugging info

class MessageHandler:
    """Handles processing and responding to user messages"""
    def __init__(self, sender_id):
        self.sender_id = sender_id
        # Load the session for this sender, or create a new session dict if not present
        self.session = user_sessions.get(sender_id, {"language": None, "ended": False, "welcome_sent": False})

    def process_message(self, message_text, quick_reply_payload=None):
        command = (quick_reply_payload or message_text).lower()

        if command in ["restart"]:
            user_sessions[self.sender_id] = {"language": None, "ended": False, "welcome_sent": False}
            self.session = user_sessions[self.sender_id]
            self.send_welcome()
            return
    
        if self.session.get("ended", False):
            return

        if not self.session.get("welcome_sent"):
            self.send_welcome()
            return
       
        if command in ["info_school_en", "info_school_ge"]: # others are included because in case the app reponds late, it takes it as text not as quick reply payload.
            self.send_info_school(command)
        elif command in ["info_preschool_en", "info_preschool_ge"]: 
            self.send_info_preschool(command)
        elif command in ["other_en", "other_ge"]:
            self.send_info_other(command)
        elif not self.session.get("language")
            self.set_language(command)  # 🔥 pass command here    
        else:
            self.send_info_after_bug()


    def send_welcome(self):
        self.session["welcome_sent"] = True
        text = responses.welcome
        quick_replies = [
            {"content_type": "text", "title": "English", "payload": "english_language_"},
            {"content_type": "text", "title": "ქართული", "payload": "georgian_language_"}
        ]
        MessengerAPI.send_message(self.sender_id, text, quick_replies)

    def set_language(self, command):
        if command == "english_language_":
            user_sessions[self.sender_id] = {"language": command, "ended": False}
            self.session = user_sessions[self.sender_id]
            MessengerAPI.send_message(self.sender_id, "You selected English.")
            self.send_menu()
        elif command == "georgian_language_":
            user_sessions[self.sender_id] = {"language": command, "ended": False}
            self.session = user_sessions[self.sender_id]
            MessengerAPI.send_message(self.sender_id, "თქვენ აირჩიეთ ქართული.")
            self.send_menu()
        else:
            self.send_info_after_bug()


    def send_menu(self):
        """Send main menu options based on language"""
        if self.session.get("language") == "english_language_":
            text = "What info can we provide?"
            quick_replies = [
                {"content_type": "text", "title": "School", "payload": "info_school_en"},
                {"content_type": "text", "title": "Preschool", "payload": "info_preschool_en"},
                {"content_type": "text", "title": "Other Question", "payload": "other_en"},
                {"content_type": "text", "title": "🔄 Restart", "payload": "restart"}
            ]
            MessengerAPI.send_message(self.sender_id, text, quick_replies)
        elif self.session.get("language") == "georgian_language_":
            text = "რა ინფორმაციის მოწოდება შეგვიძლია?"
            quick_replies = [
                {"content_type": "text", "title": "სკოლა", "payload": "info_school_ge"},
                {"content_type": "text", "title": "ფრესქული", "payload": "info_preschool_ge"},
                {"content_type": "text", "title": "სხვა შეკითხვა", "payload": "other_ge"},
                {"content_type": "text", "title": "🔄 დასაწყისი", "payload": "restart"}
            ]
            MessengerAPI.send_message(self.sender_id, text, quick_replies)

    def send_info_school(self, command):
        if self.session.get("language") == "english_language_" or command == "info_school_en":
            MessengerAPI.send_message(self.sender_id, responses.school_info_en)
        elif self.session.get("language") == "georgian_language_" or command == "info_school_ge":
            MessengerAPI.send_message(self.sender_id, responses.school_info_ge)
        # Mark conversation as ended so that further texts won't trigger a new response.
        self.session["ended"] = True
        user_sessions[self.sender_id] = self.session

    def send_info_preschool(self, command):
        if self.session.get("language") == "english_language_" or command == "info_preschool_en":
            MessengerAPI.send_message(self.sender_id, responses.preschool_info_en)
        elif self.session.get("language") == "georgian_language_" or command == "info_preschool_ge":
            MessengerAPI.send_message(self.sender_id, responses.preschool_info_ge)
        # Mark conversation as ended.
        self.session["ended"] = True
        user_sessions[self.sender_id] = self.session

    def send_info_other(self, command):
        if self.session.get("language") == "english_language_" or command == "other_en":
            MessengerAPI.send_message(self.sender_id, "Please specify your question or contact us during working hours at *+995 32 2 29 03 71*, and we'll do our best to assist you! To repeat the chat type the word: restart")
        elif self.session.get("language") == "georgian_language_" or command == "other_ge":
            MessengerAPI.send_message(self.sender_id, "გთხოვთ მოგვწერეთ კითხვა ან დაგვიკავშირდით სამუშაო საათებში *+995 32 2 29 03 71* და ვეცდებით მალე გიპასუხოთ! ჩატის ხელახლა დასაწყებად აკრიფეთ სიტყვა: restart")
        # Mark conversation as ended.
        self.session["ended"] = True
        user_sessions[self.sender_id] = self.session
    
    def send_info_after_bug(self):
        if self.session.get("language") == "english_language_":
            MessengerAPI.send_message(self.sender_id, "For detailed information, please contact us at *+995 32 2 29 03 71* during the working hours. To repeat the chat type the word: restart")
        elif self.session.get("language") == "georgian_language_":
            MessengerAPI.send_message(self.sender_id, "დეტალური ინფორმაციისთვის, გთხოვთ სამუშაო საათებში დაგვიკავშირდეთ ნომერზე *+995 32 2 29 03 71*. ჩატის ხელახლა დასაწყებად აკრიფეთ სიტყვა: restart")
        else:
            MessengerAPI.send_message(
                self.sender_id,
                "For detailed information, please contact us at *+995 32 2 29 03 71* during working hours.\n"
                "To repeat the chat, type the word: *restart*\n\n"
                "დეტალური ინფორმაციისთვის, გთხოვთ სამუშაო საათებში დაგვიკავშირდეთ ნომერზე *+995 32 2 29 03 71*.\n"
                "ჩატის ხელახლა დასაწყებად აკრიფეთ სიტყვა: *restart*"
            ) 
        
        # Mark conversation as ended.
        self.session["ended"] = True
        user_sessions[self.sender_id] = self.session


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        token_sent = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        print(f"Received token: {token_sent}")  # Debugging print
        print(f"Expected token: {VERIFY_TOKEN}")  # Debugging print
        if token_sent == VERIFY_TOKEN:
            return challenge, 200, {"Content-Type": "text/plain"}
        else:
            return "Invalid token", 403

    elif request.method == "POST":
        data = request.get_json()
        print(json.dumps(data, indent=2))  # Debugging print
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event["sender"]["id"]
                if "message" in messaging_event:
                    message = messaging_event["message"]
                    
                    # Check for quick reply payload
                    if "quick_reply" in message:
                        quick_reply_payload = message["quick_reply"]["payload"]
                        handler = MessageHandler(sender_id)
                        handler.process_message(None, quick_reply_payload)  # Pass None for message_text, use payload
                    elif "text" in message:
                        message_text = message["text"]
                        handler = MessageHandler(sender_id)
                        handler.process_message(message_text)
                        
        return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Uses Render's PORT
    print(f"Starting Flask app on port {port}...")  # Debugging print
    app.run(host="0.0.0.0", port=port, debug=True)



