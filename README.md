# OCR Text & PDF Search Engine

A full-text search engine for OCR'd PDF collections. Text is parsed into paragraphs and indexed in Elasticsearch, with a Flask backend serving search results and a simple HTML frontend for browsing and previewing the matched PDF page.

## How it works

- **`ingest.py`** — Parses OCR `.txt` files from a folder, splits them into paragraphs, tags each with a page number, and bulk-indexes them into Elasticsearch under the `book_paragraphs` index.
- **`main.py`** — Flask backend. Exposes a `/search` endpoint (phrase + fuzzy matching with highlighting) and serves the original PDFs from a `pdfs/` folder.
- **`index.html`** — Frontend. Search box on the left, results on the left panel, PDF preview (jumping to the matched page) on the right.

## Setup

1. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

2. **Set up Elasticsearch**
   Have a local Elasticsearch instance running at `https://localhost:9200` with security enabled (default `elastic` user).

3. **Configure your password**
   Create a file named `.env` in the project folder with:
   ```
   ELASTIC_PASSWORD=your_real_password
   ```
   `.env` is git-ignored and is never uploaded to the repo — keep it local only.

4. **Add your data**
   - Place OCR'd text files in `all_ocr_texts/` (one `.txt` per book, page breaks marked as `Page N` on their own line, paragraphs separated by a blank line).
   - Place the matching PDFs in `pdfs/`, using the same base filename as each `.txt` file.

5. **Index your books**
   ```
   python ingest.py
   ```

6. **Run the backend**
   ```
   python main.py
   ```
   This starts the Flask server at `http://localhost:8000`.

7. **Open the frontend**
   Open `index.html` in your browser and start searching.

## Notes

- This is set up for local development — `verify_certs=False` disables SSL certificate checking, which is fine for a local Elasticsearch instance but should not be used against a production/public server.
- `pdfs/` and `all_ocr_texts/` are git-ignored by default since they tend to be large files; you'll need to populate them yourself after cloning.
