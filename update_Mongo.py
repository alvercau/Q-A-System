import json
import os
from pymongo import MongoClient
import pandas as pd
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import HTMLConverter,TextConverter,XMLConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
import io
import os

def convert_pdf_to_txt(path):
    rsrcmgr = PDFResourceManager()
    retstr = io.StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = open(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    maxpages = 0
    caching = True
    pagenos=set()
    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, caching=caching, check_extractable=True):
        interpreter.process_page(page)
    fp.close()
    device.close()
    string = retstr.getvalue()
    retstr.close()
    return string


client = MongoClient()
db = client.lingbuzz
papers = db.get_collection('papers')

with open('../papers/urls.txt') as f:
    urls = [url.strip() for url in f.readlines()]
splitted_urls = []
for url in urls:
    splitted = url.split('/')
    for_match = ['/'.join(splitted[:3]), '/'+'/'.join(splitted[3:5]), splitted[5]]
    splitted_urls.append(for_match)
url_df = pd.DataFrame(splitted_urls)

for doc in papers.find():
    if url_df.iloc[:,1].str.contains(doc['url']).any():
        to_match = doc['url']
        url = url_df[url_df.iloc[:,1]==to_match].iloc[:,2].iloc[0]
        try: 
        	text = convert_pdf_to_txt('../papers/'+url)
            text = text.replace('\n\n', '. ').replace('\r\r', '. ')
        except:
        	pass
            print(doc['url'], doc['title'], '\n')
        papers.update_one({"url": to_match},{"$set": {"paper_raw": text}})

