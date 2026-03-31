from urllib.parse import urlparse
from messages import USER_MESSAGES
import server_conf
import regex
from quart import Quart, current_app
import re

def validate_email(email):
    email_regex = server_conf.EMAIL_REGEX
    match = regex.match(email_regex, email)
    if not match:
        return False

    domain = match.group(1).lower()
    return domain in server_conf.ALLOWED_DOMAINS

def validate_experiment_name(experiment_name):
    if not experiment_name or not isinstance(experiment_name, str):
        return False, USER_MESSAGES["INVALID_NAME_TYPE"]

    name = experiment_name.strip()
    if len(name) < 5:
        return False, USER_MESSAGES["INVALID_FULL_NAME"]

    # Unicode-aware regex for names for European names in mind (letters with diacritics, hyphens, apostrophes, spaces)
    pattern = server_conf.EXPERIMENT_NAME_REGEX
    if not regex.fullmatch(pattern, name):
        return False, USER_MESSAGES["INVALID_FULL_NAME"]

    return True, None

def validate_redirect_url(redirect_url):
    # Solution from https://stackoverflow.com/questions/7160737/how-to-validate-a-url-in-python-malformed-or-not
    if not redirect_url or not isinstance(redirect_url, str):
        return False, USER_MESSAGES["REDIRECT_URL_REQUIRED"]
    
    try:
        result = urlparse(redirect_url)
        if result:
            return True, None
        else:
            return False, USER_MESSAGES["MALFORMED_REDIRECT_URL"]
    except ValueError:
        return False, USER_MESSAGES["MALFORMED_REDIRECT_URL"]
        
def validate_experiment_tags(tags):
    for tag in tags:
        pattern = server_conf.EXPERIMENT_NAME_REGEX
        if not regex.fullmatch(pattern, tag):
            return False, USER_MESSAGES["INVALID_TAG"]
    return True, None

def validate_full_name(name):
    if not name or not isinstance(name, str):
        return False, USER_MESSAGES["INVALID_NAME_TYPE"]

    name = name.strip()
    if len(name) < 5:
        return False, USER_MESSAGES["INVALID_FULL_NAME"]

    # Unicode-aware regex for names for European names in mind (letters with diacritics, hyphens, apostrophes, spaces)
    pattern = server_conf.FULLNAME_REGEX
    if not regex.fullmatch(pattern, name):
        return False, USER_MESSAGES["INVALID_FULL_NAME"]

    return True, None

def validate_password(password):
    if len(password) < 8:
        return(USER_MESSAGES["PASSWORD_TOO_SHORT"])
    if not regex.search(r"[A-Z]", password):
        return(USER_MESSAGES["PASSWORD_NO_UPPERCASE"])
    if not regex.search(r"[a-z]", password):
        return(USER_MESSAGES["PASSWORD_NO_LOWERCASE"])
    if not regex.search(r"\d", password):
        return(USER_MESSAGES["PASSWORD_NO_DIGIT"])
    if not regex.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return(USER_MESSAGES["PASSWORD_NO_SPECIAL_CHAR"])
    return(USER_MESSAGES["PASSWORD_VALID"])

def hash_password(password):
    # From GFG: https://www.geeksforgeeks.org/password-hashing-with-bcrypt-in-flask/
    hashed_password = current_app.extensions['bcrypt'].generate_password_hash(password).decode('utf-8')
    return hashed_password

def check_password(hashed_password, password):
    # From GFG: https://www.geeksforgeeks.org/password-hashing-with-bcrypt-in-flask/
    return current_app.extensions['bcrypt'].check_password_hash(hashed_password, password)

def getExperimentFromHeaders(url):
  parsed_url = urlparse(url)
  path_parts = parsed_url.path.strip("/").split("/")  # Split path into parts
  experiment_name = path_parts[1] 
  return(experiment_name)  

def extractMediaFilePath(filename):
  parsed_filename = urlparse(filename)
  path_parts = parsed_filename.path.strip("/").split("/")
  return (path_parts[1], path_parts[2]) # Experiment name at 1 and file name with extension at 2

def is_valid_password(password) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):  # at least one uppercase letter
        return False
    if not re.search(r"[a-z]", password):  # at least one lowercase letter
        return False
    if not re.search(r"\d", password):     # at least one digit
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):  # special character
        return False
    return True
