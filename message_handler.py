import json
import responses  # This imports your responses.py from the same folder

class MessageHandler:
    """Handles processing and responding to user messages using Cloudflare KV for sessions"""
    
    def __init__(self, sender_id, env, messenger_api):
        self.sender_id = sender_id
        self.env = env
        self.api = messenger_api
        self.session = None

    async def load_session(self):
        """Check if user exists in the Cloudflare KV 'Base'"""
        data = await self.env.USER_DB.get(f"session_{self.sender_id}")
        if data:
            # RETURNING USER: Load their existing state
            self.session = json.loads(data)
        else:
            # NEW USER: (Or after you manually clear the KV base monthly)
            # They get a fresh start here.
            self.session = {"language": None, "ended": False, "welcome_sent": False}


    async def save_session(self, user_id, user_data):
    try:
        # 2,592,000 seconds = 30 days
        await self.env.USER_DB.put(
            user_id, 
            json.dumps(user_data), 
            expiration_ttl=2592000
        )
    except Exception as e:
        print(f"Error saving session: {e}")

    async def process_message(self, message_text, quick_reply_payload=None):
        await self.load_session()
        command = (quick_reply_payload or message_text).lower()

        # 1. RESTART LOGIC
        if command == "restart":
            self.session = {"language": None, "ended": False, "welcome_sent": False}
            await self.send_welcome()
            await self.save_session()
            return

        # 2. ENDED STATE CHECK
        # If they already got their info, we don't respond unless they 'restart'
        if self.session.get("ended", False):
            return

        # 3. FIRST CONTACT CHECK (The Welcome Gate)
        if not self.session.get("welcome_sent"):
            await self.send_welcome()
            await self.save_session()
            return
        
        # 4. ROUTING LOGIC (Using your responses.py)
        if command in ["info_school_en", "info_school_ge"]:
            await self.send_info_school(command)
        elif command in ["info_preschool_en", "info_preschool_ge"]: 
            await self.send_info_preschool(command)
        elif command in ["other_en", "other_ge"]:
            await self.send_info_other(command)
        elif not self.session.get("language"):
            await self.set_language(command)   
        else:
            await self.send_info_after_bug()
        
        # Save any changes made during processing
        await self.save_session()

    async def send_welcome(self):
        self.session["welcome_sent"] = True
        text = responses.welcome # Using your imported responses file
        quick_replies = [
            {"content_type": "text", "title": "English", "payload": "english_language_"},
            {"content_type": "text", "title": "ქართული", "payload": "georgian_language_"}
        ]
        await self.api.send_message(self.sender_id, text, quick_replies)

    async def set_language(self, command):
        if command == "english_language_":
            self.session.update({"language": command, "welcome_sent": True})
            await self.api.send_message(self.sender_id, "You selected English.")
            await self.send_menu()
        elif command == "georgian_language_":
            self.session.update({"language": command, "welcome_sent": True})
            await self.api.send_message(self.sender_id, "თქვენ აირჩიეთ ქართული.")
            await self.send_menu()

    async def send_menu(self):
        if self.session.get("language") == "english_language_":
            text = "What info can we provide?"
            quick_replies = [
                {"content_type": "text", "title": "School", "payload": "info_school_en"},
                {"content_type": "text", "title": "Preschool", "payload": "info_preschool_en"},
                {"content_type": "text", "title": "Other Question", "payload": "other_en"},
                {"content_type": "text", "title": "🔄 Restart", "payload": "restart"}
            ]
        else:
            text = "რა ინფორმაციის მოწოდება შეგვიძლია?"
            quick_replies = [
                {"content_type": "text", "title": "სკოლა", "payload": "info_school_ge"},
                {"content_type": "text", "title": "ფრესქული", "payload": "info_preschool_ge"},
                {"content_type": "text", "title": "სხვა შეკითხვა", "payload": "other_ge"},
                {"content_type": "text", "title": "🔄 დასაწყისი", "payload": "restart"}
            ]
        await self.api.send_message(self.sender_id, text, quick_replies)

    async def send_info_school(self, command):
        resp = responses.school_info_en if "en" in command else responses.school_info_ge
        await self.api.send_message(self.sender_id, resp)
        self.session["ended"] = True

    async def send_info_preschool(self, command):
        resp = responses.preschool_info_en if "en" in command else responses.preschool_info_ge
        await self.api.send_message(self.sender_id, resp)
        self.session["ended"] = True

    async def send_info_other(self, command):
        msg = ("Please specify your question or contact us at +995 32 2 29 03 71. Type 'restart' to begin again." 
               if "en" in command else 
               "გთხოვთ მოგვწერეთ კითხვა ან დაგვიკავშირდით +995 32 2 29 03 71. თავიდან დასაწყებად აკრიფეთ: restart")
        await self.api.send_message(self.sender_id, msg)
        self.session["ended"] = True

    async def send_info_after_bug(self):
        msg = ("For info: +995 32 2 29 03 71. Type 'restart' to repeat.\n\n"
               "დეტალური ინფორმაციისთვის: +995 32 2 29 03 71. აკრიფეთ 'restart'.")
        await self.api.send_message(self.sender_id, msg)
        self.session["ended"] = True
