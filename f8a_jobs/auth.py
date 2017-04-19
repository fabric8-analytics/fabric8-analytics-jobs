from flask import session
from flask_oauthlib.client import OAuth
import f8a_jobs.defaults as configuration

oauth = OAuth()
github = oauth.remote_app(
    'github',
    consumer_key=configuration.GITHUB_CONSUMER_KEY,
    consumer_secret=configuration.GITHUB_CONSUMER_SECRET,
    request_token_params={'scope': 'user:email'},
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize'
)


@github.tokengetter
def get_github_oauth_token():
    return session.get('auth_token')
