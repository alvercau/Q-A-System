# Lili the linguistics chatbot
__Classification, word modelling and keyword-based search project.__

Bot pipeline:
* the bot receives a question
* keywords are extracted from the question
* based on the keywords, candidate sentences are identified. These sentences contain at least one of the keywords.
* the answer is generated with multi-document summarization techniques.

## Data

Open source linguistic research articles available on [Lingbuzz](https://ling.auf.net). The papers and metadata were scraped with a [Scrapy Spider](https://github.com/alvercau/Q-A-System/blob/master/lingbuzz/lingbuzz/spiders/spider_lingbuzz.py). These papers were converted from pdf format to plain text format and inserted in the [papers database](https://github.com/alvercau/Q-A-System/blob/master/update_Mongo.py). Each document in the Mongo database has the following format:  

        {
        '_id': ObjectId('598b44c407d7df07719383e0'),
        'abstract': ['The paper will argue ...'],
        'authors': ['Yusuke Imanishi'],
        'keywords': ['resumption, possessor wh phrases, ...'],
        'published': ['To appear in Studia Linguistica'],
        'title': 'The clause-mate condition on resumption: Evidence from Kaqchikel',
        'updated_keywords': ['resumption', 'possessor', 'wh_phrases',...],
        'url': '/lingbuzz/003606'
        }


## Design

### [Classification](https://github.com/alvercau/Q-A-System/blob/master/notebooks/Classification.ipynb)
For multi-document summarization, it is necessary to assign a relevance score to each sentence, in order to be able to create some sort of ranking among them. This was obtained through a classification model. The model was trained on sentences from the abstract and sentences from examples. The first are informative, the second aren't. The [class of each sentence depends on](https://github.com/alvercau/Q-A-System/blob/master/notebooks/Feature_engineering.ipynb):
* the length of the sentence: longer sentences are more likely to be more informative than very short sentences
* number of Named Entities
* number of top [k-important](https://github.com/alvercau/Q-A-System/blob/master/notebooks/Keyword_extraction.ipynb) words
* sentence position in the doc: sentences in introductions and summaries are more likely to be relevant. 
* number of Upper Case words: often special terminology or names
* number of nouns, verbs and adjectives, as these words contain the core meaning of sentences.

K-important words are words occuring in the abstract, in the tile, in the list of keywords, or referring to an author.  

Several classification algorithms with different parameter settings were tested in order to find the one with the highest accuracy. The results for each model were very similar (about 85% accuracy). 

|Class | Precision | Recall | F1 |
| --- | --- | --- | ---|
|0 |0.87   |   0.82    |  0.85|
|1     |  0.82   |   0.87   |   0.85|

The feature importances are the following:

* k-important words: 0.24748197327746357
* upper case words: 0.22508163769671885
* position: 0.17180271002872657
* length: 0.11606623047937072
* nouns: 0.074669890591475399
* adjectives: 0.072280844601537012
* verbs: 0.051165834861816348
* named entities: 0.041450878462891659

I decided to use the Logistic regression with normalization, since this model gave me probabilities for each sentence. These probabilities are the sentences' informativeness score.


### Populate [sentence database](https://github.com/alvercau/Q-A-System/blob/master/notebooks/Sentence_database.ipynb)

The structure is as follows:

                {
                '_id': ObjectId('59a85acdb18b146ddb84ff2b'),
                'sentence': 'The second goal is to investigate the role of syntax in these patterns.',
                'paper_id' : id from origin paper in paper DB,
                'score': sentence_score predicted by classification model,
                'keywords: list of k_important words
                'similar_sentences: ID1, ID2, ...
                'type_entity': [type, word]
                }
    
[Sentence similarities](https://github.com/alvercau/Q-A-System/blob/master/notebooks/Sentence_similarity.ipynb) were determined by calculating the cosine distance between the weighted average word vectors of the nouns, verbs and adjectives in each sentence. [Word vectors](https://github.com/alvercau/Q-A-System/blob/master/notebooks/Word_model.ipynb) were computed by using a pre-trained fastText model. This model omputes vectors based on character n-grams instead of on words, which allows for more detailed vectors. For instance, all words ending in -ly (adverbs) will have vectors that are not that far from each other, even though the adverbs in question may have different meanings and hence different ddistributions. Also, words of the same lexical group (ex. quick, quickly, quicker) will have similar vectors despite their different distribution, since they share a lot of characters. Thanks to this, the model can also compute vectors for out-of-vocabulary items. Since most of the linguistic terminology was not included in any pre-trained word2vec model, and since my own word2vec model gave pretty bad results, I decided to use the fastText model. I also ran the corpus through a Gensim bigrammizer in order to identify frequent collocations (ex. sign language) and treat them as a single word.
Sentence vectors were calculated on nouns, verbs and adjectives only, since the 'gap' in sentence similarity was much bigger when taking into account only informative words than when taking into account all words. This allowed me to set a similarity threshold. 

### [Search](https://github.com/alvercau/Q-A-System/blob/master/notebooks/Search.ipynb)
Search is keyword based.  

When a question comes in, it is broken up into its words (stopwords are removed). 
* If the question starts with 'who' or 'which author', search is restricted to requesting references: keywords are looked up in the paper database.
* If the question contains an author, search is restricted to papers written by this author.

Based on the keywords, a set of candidate sentences is identified. If a sentence is present more frequently in the set of candidates (i.e., it contains more than one of the keywords), it is added to the answer. If there is a tie in frequency, the sentence with the highest score is added to the answer. In order to avoid redundancy in the answer, whenever a sentence is added, sentences that are too similar to the added sentence are eliminated from the set of candidate sentences. The summarization is broken off when the summary has the desired length or when there are no candidates left.  

The search algorithm has the following shortcomings:
* it cannot deal with out of vocabulary words. A possible work around is to look up the most [similar words](https://github.com/alvercau/Q-A-System/blob/master/notebooks/Keyword_similarity.ipynb) and check whether these are in the database. However, this made the query too complex and less accurate, so I decided to abandon this strategy.
* when questions about authors are asked, the search is limited to papers written by these authors. However, papers written by other authors may contain references to work of the queried authors that may be relevant for the summary.
* the structure of the question is not taken into account because the search is keyword based. For instance, a question like 'What do you know about tense semantics?' will result into a summary based on the keywords 'know', 'tense' and 'semantics'. It would be better to do the query on 'tense semantics' only. For this to be possible, it is necessary to automatically identify the scope of the question. In general, in English, the scope falls on the most deeply embedded verbal argument. Restricting search with taking into account the semantic structure of the question thus requires syntactic parsing of the question (or some other techniques that allow for keyword ranking).

The answer generation has the following shortcomings:
* it's slow when questions about very general things are asked
* the answer contains acronyms. It would be better to expand these.
* sentence simplification: now we have 'hanging' semantic connectors, because the sentences are simply extracted from the papers. It would be better to get rid of those that accur at the beginning of each sentence.

### [The bot](https://github.com/alvercau/Q-A-System/blob/master/search.py)
The back end of the bot itself is a Flask app. The front-end is written in CSS and JS.
