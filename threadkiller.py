import signal

class ThreadKiller:
    """This class handles SIGTERM and tells the program it's time to quit"""
    kill_now = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
    
    def exit_gracefully(self, signum, frame):
        print("\nQuitting now...")
        self.kill_now = True
