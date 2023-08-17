import sys
if sys.platform=="win32":
    #pip install keyring
    import keyring, getpass
else:
    import getpass

def getpwd(item, username):
    if sys.platform=="win32":
        pwd = keyring.get_password(item, username)
        if not pwd:
            print("Password is not saved in keyring.")
            pwd = getpass.getpass(f"Enter the password for {item} corresponding to Username:{username}: ")
    else:
        pwd = getpass.getpass(f"Enter the password for `{item}` corresponding to Username:`{username}`  : ")
    
    return pwd