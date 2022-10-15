CLIENT_ID = ""                                          # retracted for web, read from env

# auth and token endpoints
auth_url = "https://twitter.com/i/oauth2/authorize"
token_url = "https://api.twitter.com/2/oauth2/token"

# tweet processing
default_label_threshold = 0.5                           # range 0-1
max_results_per_query = 10                              # default 10, max 100
append_twitter_entity_labels = False                    # Appends "This text is about {entities}" to tweet text
resolve_mentions = False                                # @ankt_sngh -> Ankit Singh

# classification device and model
device_type = "cpu"                                     # cpu or cuda
model_name = "typeform/distilbert-base-uncased-mnli"    # "facebook/bart-large-mnli" preferred, use "typeform/distilbert-base-uncased-mnli" for heroku mem constraints
