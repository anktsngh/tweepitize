import re
from html import unescape
import config

# pose sequence as a NLI premise and label as a hypothesis
from torch import device
from transformers import AutoModelForSequenceClassification, AutoTokenizer
nli_model = AutoModelForSequenceClassification.from_pretrained(config.mnli_model)
tokenizer = AutoTokenizer.from_pretrained(config.mnli_model)


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
    # tweet = re.sub(r'@[A-Za-z0-9_]+', ' ', tweet)

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
            pred_scores = []
            for label in labels:
                premise = cleaned_tweet_text
                hypothesis = f'This text is about {label}.'

                # run through model pre-trained on MNLI
                x = tokenizer.encode(premise, hypothesis, return_tensors='pt',
                                     truncation_strategy='only_first')
                logits = nli_model(x.to(device(config.device_type)))[0]

                # Throw away "neutral" (dim 1) and take the probability of
                # "entailment" (2) as the probability of the label being true
                entail_contradiction_logits = logits[:, [0,2]]
                probs = entail_contradiction_logits.softmax(dim=1)
                pred_scores.append(probs[:, 1].item())
            tweet_obj_list.append(TweetOut(tweet['id'], cleaned_tweet_text, labels, pred_scores).__dict__)

    return tweet_obj_list


print("loaded classifier")
