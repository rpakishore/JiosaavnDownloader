import sys
import getpass

from .logger import log

if sys.platform=="win32":
    import keyring, getpass

def get_password(item: str, username: str):
    """Retrieve password from Keyring(if exist, else prompt for password)"""
    if sys.platform=="win32":
        log.debug(f'getting pwd for `{username}` in `{item}`')
        pwd = keyring.get_password(item, username)
        if not pwd:
            log.warning("Password is not saved in keyring.")
            pwd = getpass.getpass(f"Enter the password for {item} corresponding to Username:{username}: ")
            print('Consider saving the password using keyring.')
    else:
        pwd = getpass.getpass(f"Enter the password for `{item}` corresponding to Username:`{username}`  : ")
    
    return pwd

def save_password(item: str, username: str, pwd: str):
    """Saves the password to keyring"""
    assert sys.platform == "win32"
    import keyring
    keyring.set_password(item, username, pwd)
    log.info(f'Password for {item}/{username} saved to keyring')