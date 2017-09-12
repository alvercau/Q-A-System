import re
import string
from gensim.models.wrappers import FastText
from sklearn.externals import joblib
from pymongo import MongoClient
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.stop_words import ENGLISH_STOP_WORDS
from nltk.corpus import stopwords
from collections import defaultdict
from collections import Counter
import flask
import json

# Initialize the app
app = flask.Flask(__name__)

@app.route("/")
def viz_page():
    with open("index.html", 'r') as viz_file:
        return viz_file.read()


authors = joblib.load('authors')
bigrams = joblib.load('bigrams_model')
featureVec = featureVec = joblib.load('featurevec')
id_s = joblib.load('sentence_ids')

standard_stopwords = set(list(filter(lambda x: x not in ['who','what', 'which', 'when', 'where', 'how', 'why'], list(ENGLISH_STOP_WORDS)+list(stopwords.words('english')))))
df = pd.DataFrame(featureVec, index = id_s)

client = MongoClient()
db = client.lingbuzz
papers = db.get_collection('papers')
keywords = db.get_collection('keywords')
sentences = db.get_collection('sentences')
bigrams = joblib.load('bigrams_model')


def parse_question(sent):
    print('parsing question')
    """determines whether a word is English/author"""
    sentence = []
    author = []
    for w in str(sent).split():
        w = str(w)
        if w.lower() in authors:
            author.append(str(w[1:]))
        else: 
            try:
                w.encode(encoding='utf-8').decode('ascii')
                word = re.sub('[%s]' % re.escape(string.punctuation), '', w)
                if word not in standard_stopwords:
                    sentence.append(word.lower())
            except UnicodeDecodeError:
                pass
    return author, bigrams[sentence]

def most_Common(lst):
    """helper function to find most common sentence"""
    data = Counter(lst)
    return data.most_common()

def clean_sentence(sent):
    """helper function to clean sentences a little bit"""
    sent = sent.split('  ')
    out = str()
    for s in sent:
        s = s.lstrip('0123456789.- ').replace('- ', '')
        try: 
            if s[0].isupper():
                if len(s)> len(out):
                    out = s.strip()
            else:
                if out[-1] != '.':
                    out+= ' ' +s.strip()
        except:
            pass
    try: 
        if out[-1] not in ['.', '?', '!']:
            out = ''
    except:
        pass
    return out

def request_reference(q):
    print('requesting reference')
    """question is a list of strings"""
    # for this to work, the keyword entry has to be englishified. 
    # candidates = []
    answer = 'These are some papers you might want to read: \n\n'
    for candidate in papers.find({'updated_keywords': {'$in':q}}):
        answer += candidate['title'] + ', by '+ ', '.join(c for c in candidate['authors']) + '\n'
        answer += 'You can download the paper here: ling.auf.net/' + candidate['url'] + '\n\n'
    if len(answer) == 48:
    	answer = "None of the authors used '%s' as a keyword." % "' or '".join(q)
    return answer

def restrict_search(a, q):
    print('restricting search')
    paperIDs = []
    regex = '|'.join(a)
    for candidate in papers.find({'authors': {'$regex': regex}, 'updated_keywords': {'$in': q}}):
        paperIDs.append(candidate['_id'])
    if len(paperIDs) == 0:
    	for candidate in papers.find({'authors': {'$regex': regex}}):
        	paperIDs.append(candidate['_id'])
    return paperIDs

def find_candidates(q):
    print('looking for candidates')
    candidates = []
    #similar_words = []
    for candidate in keywords.find({'word': {'$in': q}}):
            #similar_words+=keywords.find_one({'word': w})['similar_words']
        candidates+=(candidate['sentenceIDs'])
    #for w in similar_words:
    #    candidates+=keywords.find_one({'_id': w})['sentenceIDs']
    return candidates

def calculate_similarities(candidates):
    print('calculating similarities')
    sub_df = df.filter(items=list(set(candidates)), axis = 0)
    cos_sim = cosine_similarity(sub_df.values)
    df_sim = pd.DataFrame(cos_sim, index = sub_df.index, columns = sub_df.index)
    similar_sent = {}
    for k in candidates:
        indexes = list(df_sim[k][df_sim[k]>0.92].index)
        if len(indexes) > 0:
            similar_sent[k] = indexes
    return similar_sent

def restrict_candidates(candidates, ids = None):
    print('found %s candidates' %len(candidates))
    print('restricting candidates')
    if ids:
        for doc in sentences.find({'_id': {'$in': candidates}, 'paperID': {'$nin': ids}}):
            candidates = list(filter(lambda x: x != doc['_id'], candidates))
    for doc in sentences.find({'_id': {'$in': candidates}, 'score': {'$lt': 0.5}}):
        candidates = list(filter(lambda x: x != doc['_id'], candidates))
    return candidates

def create_summary(q, a = None, restrict = False):
    candidates = find_candidates(q)
    out = str()
    refs = str()
    if restrict:
        ids = restrict_search(a, q)
        print('found %s papers' %len(ids)) 
        candidates = restrict_candidates(candidates, ids)
        refs = 'These are some papers you might want to read: \n\n'
        for candidate in papers.find({'_id': {'$in': ids}}):
            refs += candidate['title'].strip('.') + ', by '+ ', '.join(c for c in candidate['authors']) + '\n'
            refs += 'You can download the paper here: ling.auf.net/' + candidate['url'] + '\n\n'
    else:
        candidates = restrict_candidates(candidates)
    stack = []
    # if len(candidates) == 0 and len(out) == 0:
    #     return 'I do not have enough information to answer that question.'
    print('creating summary')
    if len(candidates) > 0:
        sentence_similarities = calculate_similarities(candidates)
        to_eliminate = []
        while (len(stack) < 5 and len(candidates)>1):
            freqs = most_Common(candidates)
            if freqs[0][1] != freqs[1][1]:
                to_append = clean_sentence(sentences.find_one({'_id': freqs[0][0]})['sentence'])
                if len(to_append.split()) > 3:
                    stack.append(to_append)
                    to_eliminate = [freqs[0][0]] + sentence_similarities[freqs[0][0]]
                else: 
                    to_eliminate = [freqs[0][0]]
                candidates = list(filter(lambda a: a not in to_eliminate, candidates))
            else: 
                sub_candidates = [_id[0] for _id in freqs if _id[1] == freqs[0][1]]
                sents = sentences.find({'_id': {'$in': sub_candidates}}).sort([('score',-1)]).limit(1)
                for sent in sents:
                    to_append = clean_sentence(sent['sentence'])
                    if len(to_append.split()) > 3:
                        stack.append(to_append)
                        to_eliminate+= [sent['_id']] + sentence_similarities[sent['_id']]
                    else:
                        to_eliminate+= [sent['_id']]
                    candidates = list(filter(lambda a: a not in to_eliminate, candidates))
        out = ' '.join(stack)
    if len(candidates) ==1:
        to_append = clean_sentence(sentences.find_one({'_id': candidates[0]})['sentence']) 
        if len(to_append.split()) > 3:
            out += to_append
    if len(out) == 0 and len(refs) == 0:
        out = 'I do not have enough information to answer that question... Sorry!'
    out += '\n\n'+ refs
    return out 

def evaluate_question(question):
    a, q = parse_question(question)
    if 'who' in q or ('which' and 'author') in q:
        return request_reference(q[1:])
    elif len(a) != 0:
        return create_summary(q[1:], a, restrict = True)
    else:
        return create_summary(q[1:])


@app.route("/", methods=["POST"])
def answer():
    data = flask.request.json
    x = data["question"]
    answer = evaluate_question(x)
    out_json = json.dumps({'answer':answer})
    print(out_json)

    return out_json
    #return out_csv

#--------- RUN WEB APP SERVER ------------#

# Start the app server on port 80
# (The default website port)
app.run(host='0.0.0.0',debug=True)



