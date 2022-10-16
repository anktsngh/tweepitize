from requests_oauthlib import OAuth2Session
from flask import Flask, request, session, url_for, render_template
from classifier import classify_tweets
import base64
import hashlib
import os
import re
import requests
import config
import json

app = Flask(__name__)
app.secret_key = config.SECRET_KEY if config.SECRET_KEY else os.getenv('SECRET_KEY')
app.debug = False

client_id = config.CLIENT_ID if config.CLIENT_ID else os.getenv('CLIENT_ID')
scopes = ["tweet.read", "users.read", "tweet.write", "offline.access"]


def make_token(redirect_uri):
    return OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes)


# Twitter API Calls

def get_all_tweets(user_id, bearer_token, fetch_retweets, max_tweets):
    params = {}
    tweets = []
    if not fetch_retweets:
        params['exclude'] = "retweets"
    fetched_tweets = 0
    if not config.limit_tweet == '-1':
        max_tweets = min(config.limit_tweet, max_tweets)
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
        tweets.extend(response['data'])
        if "next_token" in response['meta']:
            params['pagination_token'] = response['meta']['next_token']
        else:
            print("WARNING: Developer Quota Exhausted!")
            break
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
    code_verifier = base64.urlsafe_b64encode(os.urandom(30)).decode("utf-8")
    code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)

    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
    code_challenge = code_challenge.replace("=", "")

    session['code_verifier'] = code_verifier
    session['code_challenge'] = code_challenge

    app_callback_url = url_for('callback', _external=True)
    twitter = make_token(app_callback_url)
    authorization_url, state = twitter.authorization_url(config.auth_url, code_verifier=code_verifier,
                                                         code_challenge=code_challenge, code_challenge_method="S256")
    session['oauth_state'] = state
    # TODO: handle oauthlib.oauth2.rfc6749.errors.UnauthorizedClientError
    return render_template('start.html', authorization_url=authorization_url)


@app.route('/process', methods=('GET', 'POST'))
def process_tweets():
    user_dict = session['user_dict']
    tweets = get_all_tweets(user_dict['user_id'], session['token'], user_dict['rets'], user_dict['numts'])

    for tweet in tweets:
        if config.resolve_mentions:
            mentions = re.findall(r'@[A-Za-z0-9_]+', tweet["text"])
            for mention in mentions:
                try:
                    tweet['text'] = tweet['text'].replace(mention, name_from_username(mention[1:], session['token']))
                except Exception as e:
                    print(f"WARNING: could not resolve {mention[1:]}, Exception: {e}")

        if config.append_twitter_entity_labels:
            entities = []
            for annotation in tweet.get("context_annotations", []):
                entities.append(annotation["entity"]["name"])
            tweet["text"] = tweet["text"] + f". The tweet might refer to {', '.join(entities)}" if entities else ""

    session['tweet_obj_list'] = classify_tweets(tweets, user_dict['cats'])

    return "done", 200


@app.route('/result')
def initial_result():
    filtered_list = [tweet_obj for tweet_obj in session['tweet_obj_list'] if tweet_obj['label_score'] >= config.default_label_threshold]
    return render_template('callback-success.html', user_name=session['user_dict']['user_name'],
                           tweets=filtered_list, access_token_url=config.token_url)


@app.route('/delete')
def delete_tweets():
    threshold = float(request.args.get('sliderVal'))
    filtered_ids = [tweet_obj['tweet_id'] for tweet_obj in session['tweet_obj_list'] if tweet_obj['label_score'] > threshold]
    for tweet_id in filtered_ids:
        if not delete_tweet(tweet_id, session['token']):
            print(f"WARNING: Could not delete tweet ID: {tweet_id}")

    return "done", 200


@app.route('/final')
def done():
    return render_template("final.html")


@app.route('/resultUpdate')
def update_result():
    print(request.args.get('sliderVal'))
    filtered_list = [tweet_obj for tweet_obj in session['tweet_obj_list'] if tweet_obj['label_score'] >= float(request.args.get('sliderVal'))]
    return render_template('table.html', tweets=filtered_list)


@app.route('/callback', methods=('GET', 'POST'))
def callback():
    if request.method == 'GET':
        auth_code = request.args.get('code')
        app_callback_url = url_for('callback', _external=True)
        twitter = make_token(app_callback_url)
        token = twitter.fetch_token(token_url=config.token_url, client_secret=app.secret_key, code_verifier=session['code_verifier'],
                                    code=auth_code)
        session['token'] = token
        return render_template('form.html')
    else:
        # validate form fields and show progress page
        user_id, user_name = auth_user_details(session['token'])
        cats = [item.strip() for item in str(request.form.get('categoryInput')).split(",")]
        rets = True if request.form.get('includeRetweets') == "on" else False
        numts = int(request.form.get('maxTweets'))
        user_dict = {
            "user_id": user_id,
            "user_name": user_name,
            "cats": cats,
            "rets": rets,
            "numts": numts
        }
        session['user_dict'] = user_dict
        # start_time = "YYYY-MM-DDTHH:mm:ssZ"

        return render_template('processing.html')


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_message='uncaught exception'), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 33507))
    app.run("0.0.0.0", port=port)
