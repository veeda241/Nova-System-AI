class Superhero:
    def __init__(self, name):
        self.name = name

    def introduce(self):
        print("I'm a superhero.")

class IronMan(Superhero):
    def __init__(self, name):
        super().__init__(name)
        self.suit = "Iron Man suit"

    def introduce(self):
        super().introduce()
        print("My name is " + self.name + " and I wear the " + self.suit)

iron_man = IronMan("Tony Stark")
iron_man.introduce()