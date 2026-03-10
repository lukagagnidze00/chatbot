SSimport json
import responses # This imports your responses.py from the same folder
import time

class MessageHandler:
    """Handles processing and responding to user messages using Cloudflare KV for sessions"""
    
    def __init__(self, sender_id, env, messenger_api):
        self.sender_id = sender_id
        self.env = env
        self.api = messenger_api
        self.session = None

    async def load_session(self):
        """Check if user exists in the Cloudflare KV 'Base'"""
        try:
            data = await self.env.USER_DB.get(f"session_{self.sender_id}")
            if data:
                self.session = json.loads(data)
                # Ensure all keys exist to prevent 'KeyError' crashes
                if "ended" not in self.session: self.session["ended"] = False
                if "welcome_sent" not in self.session: self.session["welcome_sent"] = False
            else:
                self.session = {"language": None, "ended": False, "welcome_sent": False}
        except Exception as e:
            print(f"Load Error: {e}")
            self.session = {"language": None, "ended": False, "welcome_sent": False}


    async def save_session(self):
        """Saves session using TTL (Time To Live) for better stability"""
        try:
            # 2,592,000 seconds = 30 days
            # TTL is much safer than absolute expiration in Cloudflare
            await self.env.USER_DB.put(
                f"session_{self.sender_id}", 
                json.dumps(self.session),
                expiration_ttl=2592000 
            )
        except Exception as e:
            # If this prints in your Cloudflare logs, the KV binding 'USER_DB' is wrong
            print(f"Critical Save Error: {e}")
        
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
        elif self.session.get("language") == "georgian_language_":
            text = "რა ინფორმაციის მოწოდება შეგვიძლია?"
            quick_replies = [
                {"content_type": "text", "title": "სკოლა", "payload": "info_school_ge"},
                {"content_type": "text", "title": "ფრესქული", "payload": "info_preschool_ge"},
                {"content_type": "text", "title": "სხვა შეკითხვა", "payload": "other_ge"},
                {"content_type": "text", "title": "🔄 დასაწყისი", "payload": "restart"}
            ]
        await self.api.send_message(self.sender_id, text, quick_replies)

    async def send_info_school(self, command):
        if self.session.get("language") == "english_language_" or command == "info_school_en":
            resp = responses.school_info_en
            await self.api.send_message(self.sender_id, resp)
        elif self.session.get("language") == "georgian_language_" or command == "info_school_ge":
            resp = responses.school_info_ge
            await self.api.send_message(self.sender_id, resp)
        self.session["ended"] = True

    async def send_info_preschool(self, command):
        if self.session.get("language") == "english_language_" or command == "info_preschool_en":
            resp = responses.preschool_info_en
            await self.api.send_message(self.sender_id, resp)
        elif self.session.get("language") == "georgian_language_" or command == "info_preschool_ge":
            resp = responses.preschool_info_ge
            await self.api.send_message(self.sender_id, resp)
        self.session["ended"] = True

    async def send_info_other(self, command):
        if self.session.get("language") == "english_language_" or command == "other_en":
            msg = ("Please specify your question or contact us during working hours at *+995 32 2 29 03 71*, and we'll do our best to assist you! To repeat the chat type the word: restart.")
            await self.api.send_message(self.sender_id, msg)
        elif self.session.get("language") == "georgian_language_" or command == "other_ge":
            msg = ("გთხოვთ მოგვწერეთ კითხვა ან დაგვიკავშირდით სამუშაო საათებში *+995 32 2 29 03 71* და ვეცდებით მალე გიპასუხოთ! ჩატის ხელახლა დასაწყებად აკრიფეთ სიტყვა: restart.")
            await self.api.send_message(self.sender_id, msg)
        self.session["ended"] = True

    async def send_info_after_bug(self):
        if self.session.get("language") == "english_language_":
            msg = ("For detailed information, please contact us at *+995 32 2 29 03 71* during the working hours. To repeat the chat type the word: restart.")
            await self.api.send_message(self.sender_id, msg)
        elif self.session.get("language") == "georgian_language_":
            msg = ("დეტალური ინფორმაციისთვის, გთხოვთ სამუშაო საათებში დაგვიკავშირდეთ ნომერზე *+995 32 2 29 03 71*. ჩატის ხელახლა დასაწყებად აკრიფეთ სიტყვა: restart.")
            await self.api.send_message(self.sender_id, msg)
        else:
            msg = (
                "For detailed information, please contact us at *+995 32 2 29 03 71* during working hours.\n"
                "To repeat the chat, type the word: *restart*\n\n"
                "დეტალური ინფორმაციისთვის, გთხოვთ სამუშაო საათებში დაგვიკავშირდეთ ნომერზე *+995 32 2 29 03 71*.\n"
                "ჩატის ხელახლა დასაწყებად აკრიფეთ სიტყვა: *restart*"
            )
            await self.api.send_message(self.sender_id, msg)
        self.session["ended"] = True
