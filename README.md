# tweepitize: classify and delete your tweets with one click!

### Overview:
Tweepitize can fetch your tweets, classify or calculate relevance to your custom label(s), and delete your selection of tweets in one click. Compared to other solutions which perform a substring search, tweeptize uses an NLI-based zero-shot text classification model for advanced classification.

### Motivation:
While working on a professional project comprising of a GDPR compliance solution, I came across "Right To Be Forgotten" - especially as it relates to Twitter, one of the most powerful services on the internet. While Twitter has tools and policies much in line with the "Right To Be Forgotten", it's one thing if something can be done, and if something is feasible. Increasingly, old forgotten tweets are being used to target individuals, for instance, the newly appointed Twitter CEO himself, and an Indian journalist critical of the government. While the reaction should be better left to the subjects, as well as to the laws of the land, it's interesting how such tweets keep resurfacing. Is it that hard for one to manage their tweets? On a lighter note, I sure want my decade-old teenage tweets in favour of pineapple over pizza to be deleted before I draw the ire of the world.

While I could find [multiple tools](https://www.jeffbullas.com/twitter-tools-to-delete-tweets/) to find and delete tweets at once - all of them were keyword based and thus highly limited in their practicality. Twitter itself annotates each tweet with a domain and corresponding entity, but both are very rudimentary. Thus I wrote tweepitize (tweets + sanitize), a smart and user-friendly web application which uses Twitter APIs, OAuth 2.0, and a Zero-Shot Classification model to allow a user to fetch, filter and delete their tweets.

### Demo:
https://user-images.githubusercontent.com/15859199/196259803-a98a6365-2ad8-4c20-a94f-debcfbf290a5.mp4

