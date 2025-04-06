import os
import json
import requests
from flask import Flask, request

# Facebook API Credentials
ACCESS_TOKEN = "EAAODzm1AH0IBO2wQ2ZAJ23wu00GhnkSakkw5ierApEVhaWxISXeOWtIgHA7urmvWNqgRAf7gI5gKXxjMf3IaEdbBHgL7xgVdhf3uHwChADp96n6hflpnOJBVgc4tZARzTRN0joNOJZAZCkZAJZAE8Xo2lyiXabKQ1owEwab3ZAZBkAqwHEppw3QG0ve7IOYVEUui"
VERIFY_TOKEN = "939"

# Global dictionary to store session data for each user.
# Each entry will be a dictionary, e.g.: { "language": "ENGLISH", "ended": False }
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
        self.session = user_sessions.get(sender_id, {"language": None, "ended": False})

    def process_message(self, message_text):
        # First, check for the restart command
        if message_text.lower() in ["restart", "🔄 restart"]:
            user_sessions[self.sender_id] = {"language": None, "ended": False}
            self.session = user_sessions[self.sender_id]
            self.send_welcome()
            return

        # If conversation is ended, ignore any messages except restart
        if self.session.get("ended", False):
            # Optionally, you can notify the user that the conversation has ended
            # MessengerAPI.send_message(self.sender_id, "Conversation ended. Type 'restart' to start over.")
            return

        # If no language is set, ask for language
        if not self.session.get("language"):
            self.set_language(message_text)
        elif message_text.lower() == "info about school":
            self.send_info_school()
        elif message_text.lower() == "info about preschool":
            self.send_info_preschool()
        elif message_text.lower() == "other":
            MessengerAPI.send_message(self.sender_id, "Please specify your question, and we'll do our best to assist you!")
        else:
            self.ask_for_language()

    def send_welcome(self):
        text = "Hello, welcome to X School! Please choose your language / გთხოვთ, აირჩიეთ თქვენი ენა."
        quick_replies = [
            {"content_type": "text", "title": "English", "payload": "ENGLISH"},
            {"content_type": "text", "title": "Georgian", "payload": "GEORGIAN"}
        ]
        MessengerAPI.send_message(self.sender_id, text, quick_replies)

    def set_language(self, message_text):
        """Sets the language of the conversation based on user selection"""
        if message_text.lower() == "english":
            # Save language and mark conversation as active
            user_sessions[self.sender_id] = {"language": "ENGLISH", "ended": False}
            self.session = user_sessions[self.sender_id]
            MessengerAPI.send_message(self.sender_id, "You selected English. How can we assist you?")
            self.send_menu()
        elif message_text.lower() == "georgian":
            user_sessions[self.sender_id] = {"language": "GEORGIAN", "ended": False}
            self.session = user_sessions[self.sender_id]
            MessengerAPI.send_message(self.sender_id, "თქვენ აირჩიეთ ქართული. რით შეგვიძლია დაგეხმაროთ?")
            self.send_menu()
        else:
            self.ask_for_language()

    def ask_for_language(self):
        """Prompt the user to select a language"""
        MessengerAPI.send_message(self.sender_id, "Please choose your language / გთხოვთ, აირჩიეთ თქვენი ენა.")
        self.send_welcome()

    def send_menu(self):
        """Send main menu options based on language"""
        if self.session.get("language") == "ENGLISH":
            text = "What info can we provide?"
            quick_replies = [
                {"content_type": "text", "title": "Info about School", "payload": "INFO_SCHOOL"},
                {"content_type": "text", "title": "Info about Preschool", "payload": "INFO_PRESCHOOL"},
                {"content_type": "text", "title": "Other/Specific Question", "payload": "OTHER"},
                {"content_type": "text", "title": "🔄 Restart", "payload": "RESTART"}
            ]
            MessengerAPI.send_message(self.sender_id, text, quick_replies)
        elif self.session.get("language") == "GEORGIAN":
            text = "რა ინფორმაციის მოწოდება შეგვიძლია?"
            quick_replies = [
                {"content_type": "text", "title": "სკოლის შესახებ ინფორმაცია", "payload": "INFO_SCHOOL"},
                {"content_type": "text", "title": "ფრესქულის შესახებ ინფორმაცია", "payload": "INFO_PRESCHOOL"},
                {"content_type": "text", "title": "სხვა/კონკრეტული კითხვა", "payload": "OTHER"},
                {"content_type": "text", "title": "🔄 დასაწყისი", "payload": "RESTART"}
            ]
            MessengerAPI.send_message(self.sender_id, text, quick_replies)

    def send_info_school(self):
        if self.session.get("language") == "ENGLISH":
            MessengerAPI.send_message(self.sender_id, "Our school provides high-quality education from Grade 1 to 12. Visit our website for more details.")
        elif self.session.get("language") == "GEORGIAN":
            MessengerAPI.send_message(self.sender_id, "ჩვენი სკოლა უზრუნველყოფს მაღალხარისხიან განათლებას 1-12 კლასებში. მეტი ინფორმაციისთვის ეწვიეთ ჩვენს ვებგვერდს.")
        # Mark conversation as ended so that further texts won't trigger a new response.
        self.session["ended"] = True
        user_sessions[self.sender_id] = self.session

    def send_info_preschool(self):
        if self.session.get("language") == "ENGLISH":
            MessengerAPI.send_message(self.sender_id, "Our preschool offers early childhood education programs. Contact us for admissions.")
        elif self.session.get("language") == "GEORGIAN":
            MessengerAPI.send_message(self.sender_id, "ჩვენი preschool-ს პროგრამა გთავაზობთ ბავშვთა ადრეული აღზრდის პროგრამებს. დაგვიკავშირდით რეგისტრაციისთვის.")
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
                if "message" in messaging_event and "text" in messaging_event["message"]:
                    text = messaging_event["message"]["text"]
                    handler = MessageHandler(sender_id)
                    handler.process_message(text)
        return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Uses Render's PORT
    print(f"Starting Flask app on port {port}...")  # Debugging print
    app.run(host="0.0.0.0", port=port, debug=True)
