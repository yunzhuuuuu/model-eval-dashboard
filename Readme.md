# Retrieval Model Evaluation Dashboard

A website for learning how retrieval-based machine learning systems work, hands-on. Students will:

1. **Learn about sentence embeddings and retrieval models** — how a machine learning model converts text into numerical vectors, and how similarity between those vectors is used to find the right answer to a question.
2. **Design their own dataset of notes** — design notes that users might jot down. Each note is paired with a question someone might later ask to look that note back up, phrased differently than the note itself. This mirrors the real dataset structure used by EchoMinds, a note-taking app built by Olin students to support people who are blind or visually impaired (more information on the website).
3. **Learn evaluation metrics and evaluate ML models** — apply metrics like Recall@1, Recall@3, Mean Rank, and MRR to measure how well different embedding models retrieve the correct note for a given question, using both pre-loaded example datasets and the dataset students design themselves.

## Features

- **Dataset Explorer** — browse pre-loaded example datasets (SQuAD, and the Assistive Technology dataset used to build EchoMinds), inspecting individual question-note pairs
- **Upload your own dataset** — design a note-taking scenario, write or LLM-generate notes and matching questions, and upload two CSVs to have them automatically embedded
- **Compare 3 embedding models** — `gemini-embedding-001`, `all-mpnet-base-v2`, and `multi-qa-MiniLM-L6-dot-v1`, evaluated side by side
- **Multiple evaluation metrics** — Recall@1, Recall@3, Mean Rank, and MRR, with plain-language explanations and column tooltips built into the app

## How to run locally

1. Get a Gemini API key
- Visit https://aistudio.google.com/api-keys and create an API key.
- Create a `.streamlit/secrets.toml` file:
   ```
   GEMINI_API_KEY="your_key_here"
   ```

2. Install dependencies
   ```
   pip install -r requirements.txt
   ```

3. Run streamlit
   ```
   streamlit run app.py
   ```

## How to host the website

See the full setup guide: https://docs.google.com/document/d/1EqBUNnkiXQ5mIU2FAirTw3ojkQQJi1qUmd1vXgxq0vI/edit?usp=sharing