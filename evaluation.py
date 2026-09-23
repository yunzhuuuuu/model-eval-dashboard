import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import pandas as pd
import os

MODELS = [
    "gemini_3072",
    "all-mpnet-base-v2",
    "multi-qa-MiniLM-L6-dot-v1"
]

AVAILABLE_METRICS = ["Recall@1", "Recall@3", "Mean Rank", "MRR"]

# Session-scoped uploaded datasets are stored on disk with this separator in their filename
SESSION_SEPARATOR = "__"

def make_dataset_name(session_id, dataset_name):
    """Build the internal, session-scoped name used for files on disk."""
    return f"{session_id}{SESSION_SEPARATOR}{dataset_name}"

def display_name(internal_name, session_id):
    """Strip the session prefix off a dataset name for display purposes."""
    prefix = f"{session_id}{SESSION_SEPARATOR}"
    if session_id and internal_name.startswith(prefix):
        return f"{internal_name[len(prefix):]} (yours)"
    return internal_name

# load data
def load_datasets(session_id=None):
    """
    session_id: if provided, session-scoped datasets belonging to OTHER
    sessions are hidden. Shared/preloaded datasets (no session prefix)
    are always included.
    """
    datasets = {}
    # auto discover datasets
    for filename in os.listdir("datasets"):
        if not filename.endswith(".npz"):
            continue
        dataset_name = filename[:-4]

        if SESSION_SEPARATOR in dataset_name:
            owner_id, _ = dataset_name.split(SESSION_SEPARATOR, 1)
            if owner_id != session_id:
                continue  # belongs to a different session, skip it

        d = np.load(os.path.join("datasets", filename))
        datasets[dataset_name] = {
            "questions": d["questions"],
            "contexts": d["contexts"],
            "most_relevant": d["most_relevant_context"]
        }
    return datasets

# generate similarity rankings
def calculate_similarities(question_embeddings, context_embeddings):
    similarities = cosine_similarity(question_embeddings, context_embeddings)
    rankings = np.zeros(similarities.shape, np.int32)
    for i in range(similarities.shape[0]):
        rankings[i, :] = np.argsort(-similarities[i, :])
    return rankings

def load_rankings(session_id=None):
    all_rankings = defaultdict(dict)
    datasets = load_datasets(session_id)
    for dataset_name in datasets:
        for model in MODELS:
            q_path = (f"embeddings/" f"{dataset_name}_questions_{model}.npz")
            c_path = (f"embeddings/" f"{dataset_name}_contexts_{model}.npz")
            if not (os.path.exists(q_path) and os.path.exists(c_path)):
                continue

            question_embeddings = np.load(q_path)["embeddings"]
            context_embeddings = np.load(c_path)["embeddings"]
            rankings = calculate_similarities(question_embeddings, context_embeddings)
            all_rankings[dataset_name][model] = rankings
    return all_rankings

# evaluation methods
def recall_at_k(rankings, most_relevant, k):
    hits = 0
    for q in range(len(most_relevant)):
        if most_relevant[q] in rankings[q, :k]:
            hits += 1
    return hits / len(most_relevant)

def mean_reciprocal_rank(rankings, most_relevant):
    rr_sum = 0
    for q in range(len(most_relevant)):
        rank = np.where(rankings[q] == most_relevant[q])[0][0]
        rr_sum += 1 / (rank + 1)
    return rr_sum / len(most_relevant)

def mean_rank(rankings, most_relevant):
    """Average 1-indexed position of the correct context across all questions."""
    rank_sum = 0
    for q in range(len(most_relevant)):
        rank = np.where(rankings[q] == most_relevant[q])[0][0]
        rank_sum += (rank + 1)
    return rank_sum / len(most_relevant)

# maps metric name to function that computes it from (rankings, most_relevant)
def compute_metric(metric_name, rankings, most_relevant):
    if metric_name == "Recall@1":
        return recall_at_k(rankings, most_relevant, 1)
    elif metric_name == "Recall@3":
        return recall_at_k(rankings, most_relevant, 3)
    elif metric_name == "MRR":
        return mean_reciprocal_rank(rankings, most_relevant)
    elif metric_name == "Mean Rank":
        return mean_rank(rankings, most_relevant)
    else:
        raise ValueError(f"Unknown metric: {metric_name}")

# main
def build_results_tables(selected_metrics=None, session_id=None):
    """
    selected_metrics: list of metric names to include (subset of AVAILABLE_METRICS).
    Defaults to all available metrics if not specified.
    session_id: if provided, only this session's uploaded datasets (plus
    shared/preloaded ones) are included.
    """
    if selected_metrics is None:
        selected_metrics = AVAILABLE_METRICS

    datasets = load_datasets(session_id)
    rankings = load_rankings(session_id)
    result_tables = {}
    for dataset_name in datasets:
        most_relevant = datasets[dataset_name]["most_relevant"]
        rows = []
        for model in MODELS:
            row = {"model": model}
            if model not in rankings[dataset_name]:
                for metric in selected_metrics:
                    row[metric] = np.nan
                rows.append(row)
                continue

            r = rankings[dataset_name][model]
            for metric in selected_metrics:
                row[metric] = round(compute_metric(metric, r, most_relevant), 4)
            rows.append(row)
        label = display_name(dataset_name, session_id)
        result_tables[label] = pd.DataFrame(rows)
    return result_tables