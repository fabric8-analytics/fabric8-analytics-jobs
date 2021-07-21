"""Utility functions for User caching."""

import os
import json
import logging
import requests
import tenacity

logger = logging.getLogger(__file__)

_GEMINI_API_URL = "http://{host}:{port}/api/v1/pgsql".format(
    host=os.environ.get("GEMINI_SERVICE_HOST", "f8a-gemini-server"),
    port=os.environ.get("GEMINI_SERVICE_PORT", "5000"),)
_APP_SECRET_KEY = os.getenv('SERVICE_ACCOUNT_CLIENT_ID', 'not-set')
_ACCOUNT_SECRET_KEY = os.getenv('THREESCALE_ACCOUNT_SECRET', 'not-set')
_ENABLE_USER_CACHING = os.environ.get('ENABLE_USER_CACHING', 'true') == 'true'
_USER_CACHE_DIR = os.environ.get("USER_CACHE_DIR")


def create_cache():
    """Cache all users into PVC."""
    if _ENABLE_USER_CACHING:
        print("Starting user cache creation.")

        result = get_users_from_rds()

        if "data" in result:
            create_cache_files(result["data"])
        else:
            print("User caching failed.")
            print(result)
    else:
        print("User caching is disabled.")


@tenacity.retry(reraise=True, stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_fixed(1))
def get_users_from_rds():
    """Get all users from RDS table."""
    print("Invoking API to get user from RDS.")
    payload = "{\"query\":\"select user_id from user_details " \
              "where status = 'REGISTERED';\"}"

    try:
        response = requests.request("POST", _GEMINI_API_URL,
                                    headers={"client": "jobs",
                                             "APP_SECRET_KEY": _APP_SECRET_KEY,
                                             "x-3scale-account-secret": _ACCOUNT_SECRET_KEY,
                                             "Content-Type": "application/json"},
                                    data=payload)
        return response.json()
    except Exception as e:
        logger.error(e)
        print(e)
        return {}


@tenacity.retry(reraise=True, stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_fixed(1))
def create_cache_files(all_users):
    """Get all users and create Cache files for each user."""
    print("Creating user cache files.")
    try:
        if not os.path.exists(_USER_CACHE_DIR):
            os.makedirs(_USER_CACHE_DIR)
        else:
            # Empty the directory and create new cache
            # as few token may have been expired and files for those users need to be deleted.
            for f in os.listdir(_USER_CACHE_DIR):
                os.remove(os.path.join(_USER_CACHE_DIR, f))

        for user in all_users:
            # Create file for each user into PVC having details about user
            with open(_USER_CACHE_DIR + "/" + user[0] + ".json", 'w', encoding='utf8') as file:
                file.write("")

        print("Created cache of {} users".format(len(all_users)))
    except Exception as e:
        logger.error(e)
        print(e)


def get_user_from_cache(user_id):
    """Get User from cache."""
    print("Searching user in cache files.")
    try:
        db_cache_file_path = _USER_CACHE_DIR + "/" + user_id + ".json"

        if os.path.isfile(db_cache_file_path):
            print("Found user in cache with id %s", user_id)
            return True
        return False
    except Exception as e:
        print("User not found in cache with id %s", user_id)
        logger.error(e)
        return False


@tenacity.retry(reraise=True, stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_fixed(1))
def update_user_in_cache(user):
    """Get all users and create Cache files for each user."""
    print("Creating user in cache files.")

    if _ENABLE_USER_CACHING:
        try:
            if not os.path.exists(_USER_CACHE_DIR):
                os.makedirs(_USER_CACHE_DIR)

            # Create file for each user into PVC having details about user
            with open(_USER_CACHE_DIR + "/" + user["user_id"] + ".json", 'w',
                      encoding='utf8') as file:
                json.dump(user, file, ensure_ascii=False, indent=4, default=str)

            print("Created cache of {} user".format(len(user)))
            message = "User cache is created."
        except Exception as e:
            message = str(e)
    else:
        message = "User caching is disabled."
    return message
