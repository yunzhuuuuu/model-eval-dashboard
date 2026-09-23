import streamlit as st
import pandas as pd
import os
import subprocess
import gdown
import uuid
from csv import reader
import io

from evaluation import load_datasets, build_results_tables, make_dataset_name, display_name, AVAILABLE_METRICS
from generate_embeddings import embed_csv_dataset

st.set_page_config(
    page_title="Embedding Evaluation Dashboard",
    layout="wide"
)
st.title("Retrieval Model Evaluation Dashboard")

# Each visitor gets a random session ID the first time they load the app
if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex[:8]
session_id = st.session_state.session_id

# Soft-recommended dataset size, shown to students as guidance.
SOFT_LIMIT_CONTEXTS = 1000
SOFT_LIMIT_QANDA = 200

# Enforced hard limit to protect API key
HARD_LIMIT_ROWS = 10_000


# Preloaded example datasets (SQuAD, Assistive Technology) + their embeddings
@st.cache_resource
def download_preprocessed_data():
    if not (os.path.exists("datasets") and os.path.exists("embeddings")):
        gdown.download(id="1oqNS_vKYaTcTBJi-gJWmd6T2MSJkTTlT", output="data_and_embeddings.tar.gz", quiet=False)
        subprocess.run(["tar", "-xvzf", "data_and_embeddings.tar.gz"], check=True)
    return True

download_preprocessed_data()

tab1, tab2, tab3, tab4 = st.tabs([
    "Introduction",
    "Dataset Explorer",
    "Upload Dataset",
    "Evaluation Results"
])


# Introduction
with tab1:
    st.header("Learning Objectives")
    st.markdown("""
    This dashboard is designed to help students explore how dataset design influences the performance of retrieval models.

    Through this activity, students will:
    - Understand the evaluation metrics for retrieval models and use them to compare the performance of different models
    - Investigate how different dataset can affect retrieval accuracy
    - Design and evaluate their own retrieval datasets

    There won't be any coding involved. Students only need to create their datasets in excel forms and upload it here. 
    """)
                
    st.header("Background")
    st.markdown("""
    Students from Olin College of Engineering developed a note-taking application in summer 2025, EchoMinds, to support people who are blind or visually impaired (BVI) with machine learning. App users could store information as notes and could later retrieve that information by asking questions. The app implements a retrieval model that can match the user's question to the most relevant note instead of matching exact key words.

    For more information about retrieval models and embeddings, Read [this 2-page document](https://docs.google.com/document/d/1a8xVYLW7ON6jAQoaHGS5U2U93N3u8C0Y49vahNilTsk/edit?usp=sharing) before continuing. It's the foundation for everything else in this dashboard.
                
    """)

    st.header("Your Task")
    st.markdown("""
    You will create and evaluate their own datasets based on the scenario of a note-taking application. Read on to explore some example datasets and learn how to create and evaluate your own dataset.   
    """)


# Dataset Explorer
with tab2:
    st.header("Dataset Selection")
    datasets = load_datasets(session_id)
    st.markdown("""
    This tab lets you look inside a retrieval dataset before you evaluate it. A retrieval dataset is really just two things paired together: a set of notes, and a set of questions that each point to one correct note. Browsing an existing dataset here is the best way to understand what makes a dataset good (or not) before you try building your own in the Upload Dataset tab.

    The SQuAD and Assistive Technology datasets were used by the Olin student developers and serve as examples of retrieval datasets. You can explore them here, or you can upload your own dataset in the next tab and come back to check your own ones.

    Choose a dataset to explore.

    Each dataset contains:

    - Q&A: Information requests that a user might ask and human-annotated the context that best answers them.
    - Contexts: Notes (fact statements) that the model use to search for the answers.
    """)
    dataset_name = st.selectbox(
        "Select a dataset",
        list(datasets.keys()),
        format_func=lambda name: display_name(name, session_id)
    )
    st.caption("Not sure where to start? Try the pre-loaded datasets first to see what a good dataset looks like.")
    dataset = datasets[dataset_name]
    questions = dataset["questions"]
    contexts = dataset["contexts"]
    most_relevant = dataset["most_relevant"]

    # questions table
    st.subheader("Q&A")
    st.markdown("""
    The Questions and Answers table lists all questions and the context that has been labeled as the correct match.
    Think of this as the "answer key" for the dataset: each question has one note marked as its correct match, and that's what the retrieval model will be judged against when we evaluate it. As you browse, notice that the wording of the question often differs from the wording of its matching note — that's intentional, since a good retrieval model should find the right note by *meaning*, not by matching exact words.
    """)
    questions_df = pd.DataFrame({
        "Question ID": range(len(questions)),
        "Question": questions,
        "Correct Context": [
            contexts[idx]
            for idx in most_relevant
        ]
    })
    st.dataframe(
        questions_df,
        width="stretch",
        height=350,
        hide_index=True
    )

    # context table
    st.subheader("Contexts (First 60)")
    st.markdown("""
    The Contexts table displays the available passages or notes that can be retrieved.
    These are all the notes the retrieval model has to choose from — like the full contents of someone's note-taking app. When a question comes in, the model searches through every one of these notes (not just the 60 shown here) and ranks them by how closely their meaning matches the question. Only the first 60 contexts are shown here for easier browsing.
    """)
    contexts_df = pd.DataFrame({
        "Context ID": range(min(60, len(contexts))),
        "Context": contexts[:60]
    })
    st.dataframe(
        contexts_df,
        width="stretch",
        height=350,
        hide_index=True
    )

    # question-context pair
    st.header("Question-Context Pair Inspector")
    st.markdown("""
    Select an example question to inspect its corresponding ground-truth context.
    Use this tool to zoom in on one question-note pair at a time, so you can really see the relationship between a question and its correct note without scrolling through both big tables above. This is the same "answer key" data from the Q&A table, just shown one pair at a time for closer inspection.
    """)
    q_idx = st.number_input(
        "Question ID",
        min_value=0,
        max_value=len(questions) - 1,
        value=0,
        step=1
    )
    st.markdown("### Question")
    st.write(questions[q_idx])

    correct_context_id = most_relevant[q_idx]
    st.markdown(
        f"### Ground Truth Context (ID {correct_context_id})"
    )
    st.write(
        contexts[correct_context_id]
    )


# Upload Dataset
with tab3:
    st.header("Create your dataset")
    st.markdown(f"""
    Before you start creating your own dataset and evaluating the model performance on it, you should make sure you've explored the Dataset Explorer tab and have a sense of what a valid dataset looks like. We will also provide more examples below.

    #### Dataset Requirements

    Your dataset notes can be about any topic that could reasonably be stored in a note-taking application, including:

    - Cooking
    - Travel planning
    - Study notes
    - ......

    Your dataset must include 2 .csv files which you could create in Excel or Google Sheets and then export as .csv files. They are:

    1. context.csv
    This file contains your notes stored as sentences. Each row should contain one note. The first row should be a header row with the column name "Note". 
    Example:
    """)
    st.image("assets/contexts.png")

    st.markdown("""            
    2. qanda.csv
    This file contains questions and their correct matching note. Each row should contain one question and its corresponding note. The first row should be a header row with the column names "Question" and "Relevant Note". The "Relevant Note" column must contain the exact text of the matching note from context.csv.
    Example:
    """)
    st.image("assets/qanda.png") 

    st.markdown(f"""     
    #### Creating Your Dataset
    You can create the dataset yourself or use LLMs to generate the dataset. Make sure the questions and notes are realistic and relevant to the topic. Here's a potential prompt you can follow:
    
    ```
    I'm building a test dataset for a note-taking app's search feature. Generate [NUMBER] short notes about [YOUR TOPIC]. Each note should be 1-3 sentences, written the way a real person would jot down a quick note for themselves.
    Then, choose [NUMBER] notes, write one question for each note that a person might ask later to look up that note. The question should NOT reuse too much exact same words as the note — it should ask about the same idea in different phrasing (e.g. if the note says "Pasta: spaghetti, olive oil, garlic, cherry tomatoes, basil, parmesan cheese," a good question would be "What ingredients do I need for the pasta recipe?" not "What are the pasta ingredients I listed?").
    
    Output the results as two lists:
    1. Notes (unnumbered)
    2. Questions and their corresponding notes (unnumbered, the notes must be exactly the same as in the first list)
    ```
                
    You are also encouraged to make both by yourself and by using LLMs and explore the differences in the evaluation results.

    **Recommended dataset size:** to keep things fast to evaluate and easy to review by hand, we recommend keeping your dataset under **{SOFT_LIMIT_CONTEXTS} notes** in context.csv and under **{SOFT_LIMIT_QANDA} questions** in qanda.csv. This is just a guideline, not a hard rule -- but datasets much larger than this may take a while to embed and evaluate.
                       
    #### Before You Upload
    - Every “Relevant Note” in qanda.csv must exist exactly in context.csv.
    - You can have multiple questions that match the same note.
    - You can have notes in context.csv that are not matched to any question in qanda.csv.                
    - You should manually check that the questions and correct notes pairs are accurate and make sense.

    After uploading, embeddings will be generated automatically and the dataset will become available for evaluation.
    """)

    st.header("Upload Files")
    st.caption("Already made your two CSVs? Great — you're almost done. Just name your dataset and upload both files below.")
    st.markdown("""Give a word or short phrase to name your dataset.""")
    dataset_name = st.text_input("Dataset Name:")
    st.markdown("""Upload your two .csv files. Once you click "Save Dataset", the system will automatically generate embeddings for your dataset and save it for evaluation.""")
    context_file = st.file_uploader("Upload context", type=["csv"], key="context")
    qanda_file = st.file_uploader("Upload q&a", type=["csv"], key="qanda")

    def count_csv_data_rows(file_bytes):
        """Count rows in a CSV, excluding the header row."""
        text = file_bytes.decode("utf-8", errors="replace")
        rows = list(reader(io.StringIO(text)))
        return max(0, len(rows) - 1)

    def save_and_embed(internal_name, display_dataset_name, context_bytes, qanda_bytes, overwrite):
        dataset_dir = os.path.join("raw_data", internal_name)
        os.makedirs(dataset_dir, exist_ok=True)
        context_path = os.path.join(dataset_dir, "context.csv")
        qanda_path = os.path.join(dataset_dir, "qanda.csv")
        with open(context_path, "wb") as f:
            f.write(context_bytes)
        with open(qanda_path, "wb") as f:
            f.write(qanda_bytes)

        st.info("Dataset saved. Generating embeddings...")

        embed_csv_dataset(
            internal_name,
            context_path,
            qanda_path,
            generate_gemini_embeddings=True,
            overwrite=overwrite
        )
        st.success(f"Dataset '{display_dataset_name}' is ready and embedded. It's private to your session — other visitors won't see it.")

    if st.button("Save Dataset"):
        if not dataset_name:
            st.error("Please provide a dataset name.")
        elif "__" in dataset_name:
            st.error("Dataset name can't contain '__'. Please choose a different name.")
        elif context_file is None or qanda_file is None:
            st.error("Please upload both CSV files.")
        else:
            context_bytes = bytes(context_file.getbuffer())
            qanda_bytes = bytes(qanda_file.getbuffer())
            context_rows = count_csv_data_rows(context_bytes)
            qanda_rows = count_csv_data_rows(qanda_bytes)

            if context_rows > HARD_LIMIT_ROWS or qanda_rows > HARD_LIMIT_ROWS:
                st.error(
                    f"Dataset too large: context.csv has {context_rows} rows and qanda.csv has {qanda_rows} rows. "
                    f"Both must be under {HARD_LIMIT_ROWS} rows. Please reduce your dataset size and try again."
                )
            else:
                internal_name = make_dataset_name(session_id, dataset_name)
                dataset_path = os.path.join("datasets", f"{internal_name}.npz")
                if os.path.exists(dataset_path):
                    st.session_state.pending_overwrite = {
                        "internal_name": internal_name,
                        "display_name": dataset_name,
                        "context_bytes": context_bytes,
                        "qanda_bytes": qanda_bytes,
                    }
                else:
                    save_and_embed(internal_name, dataset_name, context_bytes, qanda_bytes, overwrite=False)

    if "pending_overwrite" in st.session_state:
        pending = st.session_state.pending_overwrite
        st.warning(f"A dataset named '{pending['display_name']}' already exists. Do you want to overwrite it?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, overwrite"):
                save_and_embed(
                    pending["internal_name"],
                    pending["display_name"],
                    pending["context_bytes"],
                    pending["qanda_bytes"],
                    overwrite=True
                )
                del st.session_state.pending_overwrite
        with col2:
            if st.button("Cancel"):
                del st.session_state.pending_overwrite


# Evaluation Results
with tab4:
    st.subheader("Evaluation Metrics")
    st.markdown("""
    This tab summarizes how well different retrieval models perform on each dataset.
    The results table provides a quantitative comparison of retrieval performance across datasets and models.

    #### The metrics used for evaluation

    - **Recall@1** measures how often the correct note is ranked first. For example, a Recall@1 score of 0.80 means the model returned the correct note as its top result for 80% of questions.
    - **Recall@3** measures how often the correct note appears within the top three results. This reflects how likely a user is to find the correct note after reviewing a small number of suggestions.
    - **Mean Rank** is the average position of the correct note in the ranked results (e.g., a Mean Rank of 2.5 means the correct note is typically found around the 2nd or 3rd spot). Lower is better.
    - **Mean Reciprocal Rank (MRR)** evaluates not only whether the correct note was retrieved, but also how highly it was ranked. Models receive higher scores when the correct note appears closer to the top of the results list.
    To better understand these metrics, read more here: [Recall vs. MRR](https://medium.com/@er111/recall-k-versus-mrr-918da3264f2a?sharedUserId=er111).
 
    A few other common retrieval metrics are **not** included above, because in this dataset every question has exactly one correct note. That single detail makes each of them turn into just another way of writing Recall@k or MRR, so they wouldn't tell us anything new:

    **A quick note on "k":** you'll see "k" in the metric names below, like Precision@**k**. It's a stand-in for a number — "how many results you're willing to look at." For example, if k=3, you'd be looking at the top three results. This is the same idea as Recall@1 and Recall@3 above, just written as a variable instead of plugging in the actual number.
 
    - **Precision@k** measures what fraction of the top-*k* retrieved results are actually relevant. Normally, if a question could have several correct notes, Precision@k and Recall@k would give different information. But here, since there's only ever one correct note, Precision@k is just Recall@k divided by k — it's the same score, only smaller and less intuitive. That's why it's left out.
    - **Hit Rate@k** measures whether *at least one* relevant result appears in the top-*k* (a yes/no per question, averaged across all questions). This distinction only matters when a question could have multiple correct notes. Since each question here has just one, "getting at least one hit" and "getting the one correct note" mean exactly the same thing — so Hit Rate@k is identical to Recall@k, just under a different name.
    - **Mean Average Precision (MAP)** averages precision at each rank where a relevant result appears, rewarding models that surface *multiple* relevant results early, then averages this across questions. It's built to reward finding several correct notes, in the right order. With only one correct note per question, that calculation simplifies down to exactly the same formula as MRR.

    #### The models being compared

    - **gemini-embedding-001** is Google's hosted embedding model, accessed through the Gemini API. It tends to capture nuanced meaning well but requires an internet connection and API calls for every embedding.
    - **all-mpnet-base-v2** is a general-purpose sentence-embedding model from the Sentence Transformers library, trained on a broad mix of text. It's the model EchoMinds itself uses.
    - **multi-qa-MiniLM-L6-dot-v1** is a smaller, faster Sentence Transformers model trained specifically for question-answering-style retrieval. It trades a bit of accuracy for much faster embedding speed.
    """)

    selected_metrics = st.multiselect(
        "Select metrics to display",
        options=AVAILABLE_METRICS
    )

    METRIC_HELP = {
        "Recall@1": "How often the correct note was the very top result. Higher is better.",
        "Recall@3": "How often the correct note showed up somewhere in the top 3 results. Higher is better.",
        "MRR": "Rewards ranking the correct note near the top, not just anywhere in the results. Higher is better.",
        "Mean Rank": "The average position of the correct note (1st, 2nd, 3rd...). Lower is better.",
    }

    if st.button("Evaluate Available Datasets"):
        if not selected_metrics:
            st.warning("Please select at least one metric.")
        else:
            st.caption("Tip: hover over a column header below (ⓘ) for a plain-language explanation of that metric.")
            results_tables = build_results_tables(selected_metrics, session_id)
            for dataset_name, table in results_tables.items():
                st.markdown(f"### {dataset_name}")
                column_config = {
                    "model": st.column_config.TextColumn(
                        "Model",
                        help="Which embedding model was used to rank the notes for this row."
                    )
                }
                for metric in selected_metrics:
                    column_config[metric] = st.column_config.NumberColumn(
                        metric,
                        help=METRIC_HELP.get(metric, ""),
                        format="%.2f"
                    )
                st.dataframe(
                    table,
                    width="stretch",
                    hide_index=True,
                    column_config=column_config
                )