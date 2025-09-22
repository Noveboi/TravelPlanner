import getpass
from os import environ


def prompt_user_for_key(key: str) -> None:
    if environ[key] is None:
        value = getpass.getpass(f'Enter key for {key}: ')
        assert len(value) > 0
        environ[key] = value