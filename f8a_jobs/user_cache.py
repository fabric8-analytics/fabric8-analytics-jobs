"""Utility functions for User caching."""

import os
import logging
import requests
import tenacity
import datetime
from f8a_jobs.defaults import (USER_CACHE_DIR,
                               GEMINI_API_URL,
                               ENABLE_USER_CACHING,
                               SERVICE_ACCOUNT_CLIENT_ID,
                               ACCOUNT_SECRET_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_cache():
    """Cache all users into PVC."""
    if ENABLE_USER_CACHING:
        logger.info("Starting user cache creation.")

        result = get_users_from_rds()

        if "data" in result:
            create_cache_files(result["data"])
            message = "User cache is created"
        else:
            message = "User caching failed."
    else:
        message = "User caching is disabled."
    logger.info(message)
    return {"message": message}


@tenacity.retry(reraise=True, stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_fixed(1))
def get_users_from_rds():
    """Get all users from RDS table."""
    logger.info("Invoking API to get user from RDS.")
    payload = "{\"query\":\"select user_id from user_details " \
              "where status = 'REGISTERED';\"}"

    try:
        response = requests.request("POST", GEMINI_API_URL,
                                    headers={"client": "jobs",
                                             "APP_SECRET_KEY": SERVICE_ACCOUNT_CLIENT_ID,
                                             "x-3scale-account-secret": ACCOUNT_SECRET_KEY,
                                             "Content-Type": "application/json"},
                                    data=payload)
        return response.json()
    except Exception as e:
        logger.error(e)
        logger.info(e)
        return {}


@tenacity.retry(reraise=True, stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_fixed(1))
def create_cache_files(all_users):
    """Get all users and create Cache files for each user."""
    logger.info("Creating user cache files.")
    try:
        if not os.path.exists(USER_CACHE_DIR):
            os.makedirs(USER_CACHE_DIR)
        else:
            # Empty the directory and create new cache
            # as few token may have been expired and files for those users need to be deleted.
            for f in os.listdir(USER_CACHE_DIR):
                os.remove(os.path.join(USER_CACHE_DIR, f))

        for user in all_users:
            # Create file for each user into PVC having details about user
            with open(USER_CACHE_DIR + "/" + user[0] + ".json", 'w', encoding='utf8') as file:
                file.write("")

        logger.info("Created cache of {} users".format(len(all_users)))
    except Exception as e:
        logger.error(e)
        logger.info(e)


def get_user_from_cache(user_id):
    """Get User from cache."""
    logger.info("Searching user in cache files.")
    try:
        db_cache_file_path = USER_CACHE_DIR + "/" + user_id + ".json"

        if os.path.isfile(db_cache_file_path):
            logger.info("Found user in cache with id %s", user_id)
            return True
        return False
    except Exception as e:
        logger.info("User not found in cache with id %s", user_id)
        logger.error(e)
        return False


@tenacity.retry(reraise=True, stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_fixed(1))
def update_user_in_cache(user):
    """Get all users and create Cache files for each user."""
    logger.info("Creating user in cache files.")

    if ENABLE_USER_CACHING:
        try:
            if not os.path.exists(USER_CACHE_DIR):
                os.makedirs(USER_CACHE_DIR)

            # Create file for each user into PVC having details about user
            with open(USER_CACHE_DIR + "/" + user["user_id"] + ".json", 'w',
                      encoding='utf8') as file:
                file.write("")

            logger.info("Created cache of {} user".format(user["user_id"]))
            message = "User cache is created."
        except Exception as e:
            message = str(e)
    else:
        message = "User caching is disabled."
    return message


def list_cached_users():
    """Get all users from cache."""
    logger.info("Listing users in cache.")
    try:
        result = []
        # Get list of all files
        file_list = os.listdir(USER_CACHE_DIR)
        for file in file_list:
            # Get each file name and created date
            if os.path.isfile(USER_CACHE_DIR + "/" + file):
                temp = os.path.getmtime(USER_CACHE_DIR + "/" + file)
                result.append([file, datetime.datetime.fromtimestamp(temp)])
        return result
    except Exception as e:
        logger.info("Error while listing all cached users ")
        logger.error(e)
        return [str(e)]
