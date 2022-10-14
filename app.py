from requests_oauthlib import OAuth2Session
from flask import Flask, request, url_for, render_template
# from classifier import classify_tweets
import base64
import hashlib
import os
import re
import requests
import config
import time
import json

app = Flask(__name__)

app.debug = False

twitter = OAuth2Session()
code_verifier = ""
oauth_store = {}
token = ""
session_dict = {}
tweet_obj_list = []


def make_token(client_id, redirect_uri, scopes):
    return OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes)


# Twitter API Calls

def get_all_tweets(user_id, bearer_token, fetch_retweets, max_tweets):
    params = {}
    tweets = []
    if not fetch_retweets:
        params['exclude'] = "retweets"
    fetched_tweets = 0
    while fetched_tweets < max_tweets:
        endpoint = f"https://api.twitter.com/2/users/{user_id}/tweets?" \
                   f"tweet.fields=context_annotations&max_results={config.max_results_per_query}"
        for key, val in params.items():
            endpoint = endpoint + '&' + key + '=' + val
        response = requests.request(
            "GET",
            endpoint,
            headers={
                "Authorization": "Bearer {}".format(bearer_token["access_token"]),
                "Content-Type": "application/json",
            },
        ).json()
        fetched_tweets += config.max_results_per_query
        if "next_token" in response['meta']:
            params['pagination_token'] = response['meta']['next_token']
        else:
            print("WARNING: Developer Quota Exhausted!")
            break
        tweets.extend(response['data'])
    return tweets


def auth_user_details(token):
    results = json.loads(requests.request(
        "GET",
        "https://api.twitter.com/2/users/me",
        headers={
            "Authorization": "Bearer {}".format(token["access_token"]),
            "Content-Type": "application/json",
        },
    ).content.decode("utf-8"))

    return results["data"]["id"], results['data']["name"]


def name_from_username(username, token):
    return json.loads(requests.request(
        "GET",
        f"https://api.twitter.com/2/users/by/username/{username}",
        headers={
            "Authorization": "Bearer {}".format(token["access_token"]),
            "Content-Type": "application/json",
        },
    ).content.decode("utf-8"))["data"]["name"]


def delete_tweet(tweet_id, token):
    return json.loads(requests.request(
        "DELETE",
        f"https://api.twitter.com/2/tweets/{tweet_id}",
        headers={
            "Authorization": "Bearer {}".format(token["access_token"]),
            "Content-Type": "application/json",
        },
    ).content.decode("utf-8"))["data"]["deleted"]

# ======================================================================================================================

# Flask App Routes


@app.route('/')
def hello():
    return render_template('index.html')


@app.route('/start')
def start():
    # note that the external callback URL must be added to the whitelist on
    # the developer.twitter.com portal, inside the app settings
    app_callback_url = url_for('callback', _external=True)

    global code_verifier, oauth_store, twitter
    code_verifier = base64.urlsafe_b64encode(os.urandom(30)).decode("utf-8")
    code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)

    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
    code_challenge = code_challenge.replace("=", "")

    scopes = ["tweet.read", "users.read", "tweet.write", "offline.access"]

    twitter = make_token(config.CLIENT_ID, app_callback_url, scopes)
    authorization_url, state = twitter.authorization_url(config.auth_url, code_verifier=code_verifier,
                                                         code_challenge=code_challenge, code_challenge_method="S256")
    # oauthlib.oauth2.rfc6749.errors.UnauthorizedClientError
    oauth_store["oauth_state"] = state
    return render_template('start.html', authorization_url=authorization_url)


@app.route('/process', methods=('GET', 'POST'))
def process_tweets():
    global tweet_obj_list
    tweets = get_all_tweets(session_dict['user_id'], token, session_dict['rets'], session_dict['numts'])

    for tweet in tweets:
        if config.resolve_mentions:
            mentions = re.findall(r'@[A-Za-z0-9]_+', tweet["text"])
            for mention in mentions:
                try:
                    tweet['text'] = tweet['text'].replace(mention, name_from_username(mention[1:], token))
                except Exception as e:
                    print(f"WARNING: could not resolve {mention[1:]}, Exception: {e}")

        if config.append_twitter_entity_labels:
            entities = []
            for annotation in tweet.get("context_annotations", []):
                entities.append(annotation["entity"]["name"])
            tweet["text"] = tweet["text"] + f". The tweet might refer to {', '.join(entities)}" if entities else ""

    # tweet_obj_list = classify_tweets(tweets, session_dict['cats'])

    time.sleep(10)
    return "done", 200


@app.route('/result')
def initial_result():
    filtered_list = [tweet_obj for tweet_obj in tweet_obj_list if tweet_obj.label_score >= config.default_label_threshold]
    return render_template('callback-success.html', user_name=session_dict['user_name'],
                           tweets=filtered_list, access_token_url=config.token_url)


@app.route('/delete')
def delete_tweets():
    global twitter, code_verifier, oauth_store, token, session_dict, tweet_obj_list
    threshold = float(request.args.get('sliderVal'))
    filtered_ids = [tweet_obj.tweet_id for tweet_obj in tweet_obj_list if tweet_obj.label_score < threshold]
    for tweet_id in filtered_ids:
        if not delete_tweet(tweet_id, token):
            print(f"WARNING: Could not delete tweet ID: {tweet_id}")

    twitter = OAuth2Session()
    code_verifier = ""
    oauth_store = {}
    token = ""
    session_dict = {}
    tweet_obj_list = []

    return "done", 200


@app.route('/final')
def done():
    return render_template("final.html")


@app.route('/resultUpdate')
def update_result():
    print(request.args.get('sliderVal'))
    filtered_list = [tweet_obj for tweet_obj in tweet_obj_list if tweet_obj.label_score >= float(request.args.get('sliderVal'))]
    return render_template('table.html', tweets=filtered_list)


@app.route('/callback', methods=('GET', 'POST'))
def callback():
    global token
    if request.method == 'GET':
        auth_code = request.args.get('code')
        token = twitter.fetch_token(token_url=config.token_url, client_secret=os.urandom(50), code_verifier=code_verifier,
                                    code=auth_code)
        return render_template('form.html')
    else:
        # validate form fields and show progress page
        global session_dict
        user_id, user_name = auth_user_details(token)
        cats = [item.strip() for item in str(request.form.get('categoryInput')).split(",")]
        rets = True if request.form.get('includeRetweets') == "on" else False
        numts = int(request.form.get('maxTweets'))
        session_dict = {
            "user_id": user_id,
            "user_name": user_name,
            "cats": cats,
            "rets": rets,
            "numts": numts
        }
        # start_time = "YYYY-MM-DDTHH:mm:ssZ"

        return render_template('processing.html')


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_message='uncaught exception'), 500


if __name__ == '__main__':
    app.run()
