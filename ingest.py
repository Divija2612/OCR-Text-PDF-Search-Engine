import os#importing os library for checking if path exists like os.path.exists() and for listing files in a directory like os.listdir()
import re#regular expression like re.match() to find page numbers in the OCR text
from elasticsearch import Elasticsearch, helpers #helpers provide useful utilities for bulk operations and other tasks like help like helpers.bulk() for bulk indexing, helpers.scan() for scrolling through large result sets, and helpers.reindex() for reindexing data from one index to another
from dotenv import load_dotenv

load_dotenv()
ELASTIC_PASSWORD = os.environ["ELASTIC_PASSWORD"]
# Connect securely using the default local server credentials
es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", ELASTIC_PASSWORD),
    verify_certs=False # Disables SSL warning check for local sandbox development
)

INDEX_NAME = "book_paragraphs" #the name of the index to be created in Elasticsearch

def create_index():#every paragraph goes into book paragraphs index, with doc_id, paragraph_id, page_number, text_content, pdf_filename as fields like database in sql holds tables 
    settings_mapping = {#Defines the mappings for Elasticsearch like a schema in a relational database, specifying the data types and analyzers for each field in the documents to be indexed
        "mappings": {#Defines the structure of every document
            "properties": {#lists every field in the document and its data type, like a schema in a relational database
                "doc_id": {"type": "keyword"},#not searchable, used for filtering and aggregations
                "paragraph_id": {"type": "keyword"},#store as it is
                "page_number": {"type": "integer"},
                "text_content": {"type": "text", "analyzer": "standard"},#users searchable text, analyzed for full-text search and this is where Elasticsearch automatically breaks into words, lowercases and indexes
                "pdf_filename": {"type": "keyword"}#store as it is
            }
        }
    }
    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME, body=settings_mapping)
        print(f"Index '{INDEX_NAME}' created successfully.")

def parse_and_prepare_chunks(file_path, doc_id, pdf_filename):#input ocr text and output elasticsearch documents, each paragraph is a document with its own unique id and page number
    actions = []#stores every paragraph as a document to be indexed in Elasticsearch and later all are indexed in bulk for efficiency using helpers.bulk()
    current_page = 0 #without page number, it will be 0, if page number is found, it will be updated before reading the next paragraph in ocr
    
    with open(file_path, 'r', encoding='utf-8') as f:#opens ocr text file in read mode with utf-8 encoding, which is important for handling special characters and symbols that may appear in the text
        content = f.read()#everything becomes 1 string, paragraphs are separated by 2 new lines, so we can split them into a list of paragraphs
    
    raw_paragraphs = content.split('\n\n')#twice \n means it is a blank line
    paragraph_counter = 0

    for raw_para in raw_paragraphs:#processes every paragraph, checks if it is a page number or unnumbered page, and prepares the document for Elasticsearch
        clean_para = raw_para.strip()#removes spaces, extra new lines, and other whitespace characters from the beginning and end of the paragraph text
        if not clean_para:#skip the blank paragraphs
            continue
            
        # Matches lines like "Page 1", "Page 3", etc.
        page_match = re.match(r'^Page\s+(\d+)$', clean_para, re.IGNORECASE)#pattern to find page numbers in the OCR text, ignoring case sensitivity, and capturing the numeric part of the page number for later use as given in the ocr texts provided by the user, page numbers are written as "Page 1", "Page 2", etc. and this regex pattern captures that format
        if page_match:
            current_page = int(page_match.group(1))#group(1) captures the numeric part of the page number, which is then converted to an integer and stored in current_page for later use when creating the document for Elasticsearch use group(0) to get the whole match, group(1) to get the first captured group, and so on. In this case, we only have one captured group for the page number.
            continue
        elif clean_para.lower() == "unnumbered page":#some ocrs having unnumbered pages can be skkipped
            continue
            
        paragraph_counter += 1#moves to next paragraphs
        paragraph_id = f"{doc_id}_p{paragraph_counter:04d}"#create paragraph id with doc_id and paragraph number, padded with zeros for consistent length 4 digits for better sorting and searching, e.g., "book_p0001", "book_p0002", etc.
        
        doc = {#create document to be indexed in Elasticsearch, with doc_id, paragraph_id, page_number, text_content, pdf_filename as fields
            "_index": INDEX_NAME,
            "_id": paragraph_id,
            "_source": {
                "doc_id": doc_id,
                "paragraph_id": paragraph_id,
                "page_number": current_page,
                "text_content": clean_para,
                "pdf_filename": pdf_filename
            }
        }#this basically inside es is { "doc_id":"book", "paragraph_id":"book_p0001", "page_number":8, "text_content":"Operating Systems...", "pdf_filename":"book.pdf"}
        actions.append(doc)
        
    return actions

def main():
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    create_index()
    
    # Path to the folder containing ALL your raw OCR text files
    ocr_folder_path = "all_ocr_texts" 
    
    if os.path.exists(ocr_folder_path):
        print(f"Scanning '{ocr_folder_path}' directory for book datasets...")
        
        # Loop through every text file in the directory
        for filename in os.listdir(ocr_folder_path):
            if filename.endswith(".txt"):
                file_path = os.path.join(ocr_folder_path, filename)
                
                #a clean doc_id (like 'norris_miscellanies')
                doc_id = filename.replace(".txt", "").lower()
                pdf_filename = filename.replace(".txt", ".pdf")
                
                print(f"Parsing and chunking text metadata for: {filename}...")
                actions = parse_and_prepare_chunks(file_path, doc_id, pdf_filename)
                
                if actions:
                    print(f"Bulk indexing {len(actions)} segments into Elasticsearch...")
                    helpers.bulk(es, actions)
                    
        print("\n ALL book texts successfully processed and fully indexed inside Elasticsearch!")
    else:
        print(f"Error: Target directory '{ocr_folder_path}' cannot be found.")
if __name__ == "__main__":
    main()
#main idea: ngest.py is a data loading script. 
#Its job is to take the OCR text from a PDF and store it in Elasticsearch so it can be searched later.