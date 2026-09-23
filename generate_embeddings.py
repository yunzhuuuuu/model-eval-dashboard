import numpy as np
from sentence_transformers import SentenceTransformer
import os
from google import genai
from google.genai.errors import ClientError
import streamlit as st

from evaluation_core.datasets import load_csv_dataset
from evaluation_core.embeddings import (
    embed_gemini_batches,
    encode_sentence_transformer,
)

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

def gemini_embedded(texts, label):
    # get gemini embeddings
    BATCH_SIZE = 99   # max requests per minute is 100 for gemini free plan
    countdown_placeholder = None

    def show_retry_countdown(remaining, _error):
        nonlocal countdown_placeholder
        if countdown_placeholder is None:
            countdown_placeholder = st.empty()
        countdown_placeholder.warning(
            f"Gemini quota exceeded. Retrying in {remaining} seconds. Please don't leave the page."
        )

    embeddings = embed_gemini_batches(
        client,
        texts,
        batch_size=BATCH_SIZE,
        is_retryable=lambda error: (
            isinstance(error, ClientError)
            and "RESOURCE_EXHAUSTED" in str(error)
        ),
        on_retry_countdown=show_retry_countdown,
    )
    if countdown_placeholder is not None:
        countdown_placeholder.empty()

    print(f"saving gemini embeddings {label} {embeddings.shape}")
    np.savez(f"{label}.npz", embeddings=embeddings)

# def embed_assistive_tech(generate_gemini_embeddings=False):
#     with open("assistive_technotes_320.csv") as f:
#         facts = reader(f)
#         contexts = [fact[1] for fact in facts]
#         contexts = contexts[1:]

#     with open("assistive_technotes_qanda.csv") as f:
#         r = reader(f)
#         q_and_as, most_relevant = zip(*[(q_and_a[1], q_and_a[2]) for q_and_a in r])
#         questions = q_and_as[1:]
#         most_relevant = most_relevant[1:]
#         most_relevant_indices = [contexts.index(m) for m in most_relevant]
#     embed_dataset("assistive_technology_320", questions, contexts, most_relevant_indices, generate_gemini_embeddings)

def embed_csv_dataset(dataset_name, facts_csv, qa_csv, generate_gemini_embeddings=False, overwrite=False):
    dataset_path = f"datasets/{dataset_name}.npz"
    if os.path.exists(dataset_path):
        if not overwrite:
            print(f"Dataset '{dataset_name}' already embedded, skipping...")
            return
        print(f"Dataset '{dataset_name}' already exists, overwriting...")
        clear_existing_dataset_files(dataset_name)

    dataset = load_csv_dataset(
        facts_csv,
        qa_csv,
        add_missing_contexts=True,
    )
    for context in dataset.added_contexts:
        print(f"Context from Q&A file missing:\n{context}. Adding to facts list")

    embed_dataset(
        dataset_name,
        list(dataset.questions),
        list(dataset.contexts),
        list(dataset.most_relevant),
        generate_gemini_embeddings,
    )

def clear_existing_dataset_files(dataset_name):
    """Remove a previously generated dataset + its embeddings, so it can be regenerated from scratch."""
    dataset_path = f"datasets/{dataset_name}.npz"
    if os.path.exists(dataset_path):
        os.remove(dataset_path)
    if os.path.exists("embeddings"):
        for filename in os.listdir("embeddings"):
            if filename.startswith(f"{dataset_name}_questions_") or filename.startswith(f"{dataset_name}_contexts_"):
                os.remove(os.path.join("embeddings", filename))

# def embed_squad(generate_gemini_embeddings=False):
#     dataset = load_dataset("squad", split='validation')
#     questions = dataset["question"]
#     contexts = dataset["context"]

#     # Build unique context set (many questions share the same paragraph)
#     unique_contexts = list(dict.fromkeys(contexts))
#     context_to_index = {c: i for i, c in enumerate(unique_contexts)}
#     most_relevant_context = [context_to_index[c] for c in contexts]
#     embed_dataset('squad_1_1', questions, unique_contexts, most_relevant_context, generate_gemini_embeddings)

def embed_dataset(dataset_name, questions, contexts, most_relevant_context, generate_gemini_embeddings=False):
    print(f"Questions: {len(questions)}")
    print(f"Contexts: {len(contexts)}")
    np.savez(f"datasets/{dataset_name}.npz", questions=questions, contexts=contexts, most_relevant_context=most_relevant_context)
    if generate_gemini_embeddings:
        gemini_embedded(questions, f"embeddings/{dataset_name}_questions_gemini_3072")
        gemini_embedded(contexts, f"embeddings/{dataset_name}_contexts_gemini_3072")

    # a faster model
    model = SentenceTransformer("multi-qa-MiniLM-L6-dot-v1")
    embed_sentence_transformer(model, questions, f"embeddings/{dataset_name}_questions_multi-qa-MiniLM-L6-dot-v1.npz")
    embed_sentence_transformer(model, contexts, f"embeddings/{dataset_name}_contexts_multi-qa-MiniLM-L6-dot-v1.npz")

    # the EchoMinds model
    model = SentenceTransformer("all-mpnet-base-v2")
    embed_sentence_transformer(model, questions, f"embeddings/{dataset_name}_questions_all-mpnet-base-v2.npz")
    embed_sentence_transformer(model, contexts, f"embeddings/{dataset_name}_contexts_all-mpnet-base-v2.npz")

def embed_sentence_transformer(model, texts, label):
    embeddings = encode_sentence_transformer(model, texts)
    np.savez(label, embeddings=embeddings)

# if __name__ == "__main__":
#     # embed_squad()
#     dataset1 = "assistive_technology_320"
#     dataset2 = "cooking"
#     embed_csv_dataset(
#         dataset1,
#         f"raw_data/{dataset1}/facts.csv",
#         f"raw_data/{dataset1}/qanda.csv"
#     )
#     embed_csv_dataset(
#         dataset2,
#         f"raw_data/{dataset2}/facts.csv",
#         f"raw_data/{dataset2}/qanda.csv"
#     )