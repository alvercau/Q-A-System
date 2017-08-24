# Q-A-System
__Lili the chatbot that answers questions about linguistics.__
Classification and unsupervised learning to populate Q-A database.

From input question, extract:
* type of entity we are looking for (person, date, fact, definition, general)
* keywords

To find answer: multi-doc summarization.  
Find docs that contain the keywords in question, check whether they contain the required entity type.
For candidate docs, calculate sentence scores. Start summary with sentence with highest scores. Exclude sentences that are too similar to sentences that were already added to the stack to avoid redundancy. Stop when summary has desired length and return answer.
Decision:
* If too many candidates: 'The question is too broad to answer in a couple of lines' + recommend literature
* If not enough candidates: 'Sorry, I do not have enough information to answer your question'
* Else: return answer.

## Data

Open source linguistic research articles available on [Lingbuzz](https://ling.auf.net).

## Design

### Scraping meta data with Scrapy

* title
* authors
* year
* publication status
* abstract
* keywords
* url to pdf


### Database

* Insert scraped meta data in MongoDB
* Download papers
* Convert papers to text
* Get rid of all sentences with non-English words or unicode characters to diminish noise.
* Insert converted and cleaned papers in MongoDB

### Multi-doc summarization
Assign score to trigrammized sentences based on following features:
* Length of sentence
* Number of Named Entities
* Number of top K-important words (see __keyword extraction__)
* Sentence position in the doc: sentences in introductions and summaries are more likely to be relevant. The problem is that after conversion, the docs do not have much of a structure, they are basically a huge string. It should be possible to recover some structure based on number of white lines and words such as 'section', 'chapter', '1.' etc.
* Number of Upper Case words: often special terminology or names
* Number of nouns, verbs and adjectives

Normalization:
* sentence position to %
* other features: sigmoid function

Classification to optimize weights of the features:
* Train logistic regression model based on sentences in abstracts (1) and sentences in examples (0)
* Retain the optimal parameters to calculate sentence scores.

### Keyword extraction
Some words are more relevant for doc summarization than others. These words have the following properties:
* occur in abstract
* occur in keyword list (tokenized and trigrammized)
* occur in title
* occur in conclusion
* first occurence at the beginning of the document
* high TFIDF score
* words that revealed to be topic-relevant in topic modeling

### Populate database with sentences and scores
* sentence
* score
* list of top K-important words
* list of types of entities in sentence
* TFIDF vector to calculate similarity with other sentences.

### Make bot
