from transformers import pipeline
import re
from html import unescape

classifier = pipeline("zero-shot-classification",
                      model="facebook/bart-large-mnli")


class TweetOut:
    def __init__(self, tweet_id, text, labels, label_scores):
        self.tweet_id = tweet_id
        self.text = text
        self.label_score = max(label_scores)
        self.label = labels[label_scores.index(self.label_score)]


def clean_tweet(text):
    # unescape HTML entities
    tweet = unescape(text)

    # remove old style retweet text "RT"
    tweet = re.sub(r'^RT[\s]+', '', tweet)

    # remove hyperlinks
    tweet = re.sub(r'https?:\/\/.*[\r\n]*', '', tweet)
    # remove newline chars
    tweet = re.sub(r'\n+', ' ', tweet)

    # remove hashtags
    # only removing the hash # sign from the word
    tweet = re.sub(r'#', '', tweet)

    # remove mentions
    tweet = re.sub(r'@[A-Za-z0-9]+', ' ', tweet)

    # remove punctuations like quote, exclamation sign, etc.
    # we replace them with a space
    # tweet = re.sub(r'[' + string.punctuation + ']+', ' ', tweet)

    return tweet.strip()


def classify_tweets(tweets, labels):
    # sequence_to_classify = "one day I will see the world"
    # candidate_labels = ['travel', 'cooking', 'dancing']
    # print(classifier(sequence_to_classify, candidate_labels))

    # multi_class = len(labels) > 1
    tweet_obj_list = []

    for tweet in tweets:
        cleaned_tweet_text = clean_tweet(tweet['text'])
        if cleaned_tweet_text:
            pred = classifier(cleaned_tweet_text, labels)
            tweet_obj_list.append(TweetOut(tweet['id'], cleaned_tweet_text, pred['labels'], pred['scores']))

    return tweet_obj_list


print("loaded classifier")
