import datetime

class Jarvis:
    def __init__(self):
        self.greeting = "Hello, I'm JARVIS."

    def get_time(self):
        return datetime.datetime.now().strftime("%H:%M:%S")

    def get_greeting(self):
        return self.greeting

jarvis = Jarvis()
print(jarvis.get_greeting())
print("Current time: " + jarvis.get_time())