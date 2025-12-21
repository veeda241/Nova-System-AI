class Feedback:
    def __init__(self):
        self.responses = []

    def add_response(self, response):
        self.responses.append(response)

    def display_responses(self):
        for response in self.responses:
            print(response)

feedback = Feedback()
feedback.add_response("Your responses are super.")
feedback.display_responses()