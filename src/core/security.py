from bcrypt import hashpw, gensalt, checkpw


def get_password_hash(password: str) -> str:
    salt = gensalt()
    return hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    return checkpw(password.encode(), hashed_password.encode())