import os
import urllib3#importing urllib3 to disable SSL warnings for local development
from elasticsearch import Elasticsearch
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# Clean up console warnings for local development SSL bypass
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)#creates empty web server instance, which will be used to handle incoming HTTP requests and route them to the appropriate functions

# Enable CORS so your local HTML frontend file can request data safely
CORS(app)

# Elasticsearch setup - password now comes from the environment, never hardcoded
ELASTIC_PASSWORD = os.environ["ELASTIC_PASSWORD"]
es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", ELASTIC_PASSWORD),
    verify_certs=False
)

INDEX_NAME = "book_paragraphs"#contains paragraph id, page number, text, and filename
PDF_DIRECTORY = "pdfs"#folder where all the PDFs are stored, so that the backend can serve them to the frontend when requested

# Route to statically serve your PDF files from the 'pdfs' directory
@app.route('/pdfs/<path:filename>')
def serve_pdf(filename):
    return send_from_directory(PDF_DIRECTORY, filename)#send the requested PDF file from the pdfs directory to the browser, allowing users to view or download the original PDF
#sends the requested PDF to the browser
# Search endpoint mapping to Elasticsearch
@app.route('/search', methods=['GET'])
def search():
    q = request.args.get('q', '').strip()#get the query parameter from the URL, e.g., /search?q=python, and remove any leading/trailing whitespace
    if not q:
        return jsonify({"error": "Empty query"}), 400

    #advanced Multi-Match Query with Exact Phrase Boosting & Fallback Fuzziness
    query_body = {
        "query": {
            "bool": {#allows combining multiple query clauses, like must, should, and filter, to create complex search logic
                "should": [#"should" means that at least one of the following conditions should match, but it's not mandatory for all to match and higher score is given to documents that match more of these conditions
                    # 1. Give maximum priority to exact phrase matching
                    {
                        "match_phrase": {
                            "text_content": {
                                "query": q,
                                "boost": 3.0#importance
                            }
                        }
                    },
                    # 2. Fallback to fuzzy search if there are typos or old-English variants
                    {
                        "match": {
                            "text_content": {
                                "query": q,
                                "fuzziness": "AUTO",
                                "operator": "or",
                                "boost": 1.0#normal importance
                            }
                        }
                    }
                ]
            }
        },
        #request Elasticsearch to return highlighted text fragments
        "highlight": {
            "fields": {
                "text_content": {}
            },
            "pre_tags": ["<mark style='background-color: #ffeb3b; padding: 2px 4px; border-radius: 3px;'>"],
            "post_tags": ["</mark>"]#after word inserted browser shows highlighted word with yellow background
        },
        "size": 10
    }

    try:
        response = es.search(index=INDEX_NAME, body=query_body)#sends query to Elasticsearch, asking it to search the book_paragraphs index using the defined query_body, and returns the search results in the response variable
        hits = response['hits']['hits']#actual search results are nested inside the 'hits' key of the response, and we extract them for further processing
        results = []
        for hit in hits:
            source = hit['_source']#get the original document data from the search hit, which contains fields like paragraph_id, page_number, text_content, and pdf_filename
            
            #if Elasticsearch generated an intelligent highlighted snippet,we use it
            #otherwise, fallback to the raw text content.
            highlighted_text = source['text_content']
            if 'highlight' in hit and 'text_content' in hit['highlight']:
                highlighted_text = "... " + " ... ".join(hit['highlight']['text_content']) + " ..."

            results.append({
                "score": hit['_score'],
                "paragraph_id": source['paragraph_id'],
                "page_number": source['page_number'],
                "text_content": highlighted_text, # Contains visual HTML highlighting tags now
                "pdf_url": f"http://localhost:8000/pdfs/{source['pdf_filename']}"#creates a clickable link to the original PDF file, allowing users to view or download the source document directly from the search results
            })
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Start the Flask app server on port 8000
    app.run(host="0.0.0.0", port=8000, debug=True)
#core idea: In simple terms, main.py is the backend server of your project.
#Its job is to accept search requests from users, search Elasticsearch, and return the results.
#What main.py does
#Starts a web server
#Uses Flask (or FastAPI in your earlier version) to create a backend running on localhost:8000.
#Connects to Elasticsearch
#Logs into your local Elasticsearch database where all the book paragraphs are stored.
#Serves PDF files
#Makes the pdfs/ folder accessible so users can open the original PDF.
#Provides a Search API

#When a user searches, for example:

#/search?q=python

#it receives the word "python".

#Searches Elasticsearch
#Looks for matching paragraphs in the book_paragraphs index.
#Returns the results
#Sends back the:
#paragraph text
#page number
#relevance score
#PDF link

#The frontend then displays these results to the user.