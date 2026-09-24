type IntroductionProps = {
  onContinue: () => void;
};

export function IntroductionSection({ onContinue }: IntroductionProps) {
  return (
    <div className="section-stack">
      <header className="page-heading intro-heading">
        <p className="eyebrow">Introduction</p>
        <h1>Retrieval Model Evaluation Dashboard</h1>
        <p>
          Explore how dataset design influences retrieval-model performance,
          then create and evaluate a dataset of your own—no coding required.
        </p>
      </header>

      <section className="content-card intro-section intro-objectives">
        <div className="section-heading">
          <p className="eyebrow">Learning objectives</p>
          <h2>What you will learn</h2>
          <p>
            This dashboard is designed to help students explore how dataset
            design influences the performance of retrieval models. You only need
            Excel or Google Sheets—the activity does not involve coding.
          </p>
        </div>
        <ul className="learning-list">
          <li>
            <span>01</span>
            <div>
              <h3>Understand evaluation metrics</h3>
              <p>
                Read Recall@1, Recall@3, Mean Rank, and MRR, then use them to
                compare model performance.
              </p>
            </div>
          </li>
          <li>
            <span>02</span>
            <div>
              <h3>Investigate dataset effects</h3>
              <p>
                See how wording, topic, and dataset structure can change
                retrieval accuracy.
              </p>
            </div>
          </li>
          <li>
            <span>03</span>
            <div>
              <h3>Design your own test</h3>
              <p>
                Create realistic notes and questions, upload the two CSV files,
                and evaluate three models.
              </p>
            </div>
          </li>
        </ul>
      </section>

      <section className="content-card intro-section intro-background">
        <div className="intro-copy">
          <p className="eyebrow">Background</p>
          <h2>From EchoMinds to this lab</h2>
          <p>
            In summer 2025, Olin College students developed EchoMinds, a
            note-taking application designed to support people who are blind or
            visually impaired. Users save information as notes, then retrieve it
            later by asking natural-language questions.
          </p>
          <p>
            Instead of requiring exact keywords, an embedding model looks for
            notes with similar meaning. This dashboard lets you test how reliably
            different models find the human-labeled correct note.
          </p>
          <a
            className="text-link"
            href="https://docs.google.com/document/d/1a8xVYLW7ON6jAQoaHGS5U2U93N3u8C0Y49vahNilTsk/edit?usp=sharing"
            target="_blank"
            rel="noreferrer"
          >
            Read the 2-page background about retrieval models and embeddings
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        </div>
        <div
          className="retrieval-visual"
          aria-label="A question is matched to its most relevant note"
        >
          <div className="query-chip">
            <span>Question</span>
            What ingredients do I need for pasta?
          </div>
          <div className="signal-lines" aria-hidden="true">
            <i />
            <i />
            <i />
          </div>
          <div className="note-stack">
            <div className="mini-note faded">Dentist appointment: Tuesday at 3</div>
            <div className="mini-note winner">
              <span>Best match · 94%</span>
              Pasta: spaghetti, olive oil, garlic, tomatoes, basil…
            </div>
            <div className="mini-note faded">Remember to water the herbs</div>
          </div>
        </div>
      </section>

      <section className="content-card intro-section task-card">
        <div className="intro-task-copy">
          <p className="eyebrow">Your task</p>
          <h2>Explore, create, compare</h2>
          <p>
            Create and evaluate your own dataset for a note-taking application.
            Start by exploring examples, then build a scenario of your own.
          </p>
        </div>
        <ol className="task-list">
          <li>
            <span>1</span>
            Browse an example dataset and inspect question-note pairs.
          </li>
          <li>
            <span>2</span>
            Create two CSV files about a topic you choose.
          </li>
          <li>
            <span>3</span>
            Upload them and compare the model results.
          </li>
        </ol>
      </section>

      <section className="intro-next-step" aria-labelledby="intro-next-step-title">
        <div>
          <p className="eyebrow">Next step</p>
          <h2 id="intro-next-step-title">See retrieval in action</h2>
          <p>
            Begin with a prepared dataset, then return to upload and compare
            your own.
          </p>
        </div>
        <div className="intro-next-actions">
          <button type="button" className="button primary" onClick={onContinue}>
            Start with an example
            <span aria-hidden="true">→</span>
          </button>
        </div>
      </section>
    </div>
  );
}
