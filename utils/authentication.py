import os

def create_session_id():
    return os.urandom(16).hex()