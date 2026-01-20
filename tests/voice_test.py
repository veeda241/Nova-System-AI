import pyttsx3
try:
    print("Init...")
    engine = pyttsx3.init()
    print("Init success.")
    print("Speaking...")
    engine.say("Testing voice")
    engine.runAndWait()
    print("Speak success.")
except Exception as e:
    print(f"Caught error: {e}")
except TypeError as e:
    print(f"Caught TypeError: {e}")
except:
    print("Caught unknown error")
print("Done")
