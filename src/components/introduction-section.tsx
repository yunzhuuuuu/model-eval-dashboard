type IntroductionProps = {
  onContinue: () => void;
};

export function IntroductionSection({ onContinue }: IntroductionProps) {
  return (
    <div className="section-stack">
      <section className="hero-card">
        <div className="hero-copy">
          <p className="eyebrow">Retrieval model evaluation</p>
          <h1>What makes a note easy for a model to find?</h1>
          <p className="hero-lede">
            Explore real retrieval datasets, compare three embedding models, and
            design a dataset of your own—no coding required.
          </p>
        </div>
        <div className="retrieval-visual" aria-label="A question is matched to its most relevant note">
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

      <section className="content-card">
        <div className="section-heading">
          <p className="eyebrow">Learning objectives</p>
          <h2>By the end, you will be able to…</h2>
        </div>
        <div className="objective-grid">
          <article>
            <span className="objective-number">01</span>
            <h3>Read retrieval metrics</h3>
            <p>
              Understand Recall@1, Recall@3, Mean Rank, and MRR, then use them
              to compare model performance.
            </p>
          </article>
          <article>
            <span className="objective-number">02</span>
            <h3>Spot dataset effects</h3>
            <p>
              Investigate how the wording, topic, and structure of a dataset
              change retrieval accuracy.
            </p>
          </article>
          <article>
            <span className="objective-number">03</span>
            <h3>Design your own test</h3>
            <p>
              Build a realistic note-and-question dataset, upload it, and
              evaluate it across three models.
            </p>
          </article>
        </div>
      </section>

      <section className="story-grid">
        <article className="content-card">
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
        </article>
        <article className="content-card task-card">
          <p className="eyebrow">Your task</p>
          <h2>Explore, create, compare</h2>
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
        </article>
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
          <a
            className="text-link"
            href="https://docs.google.com/document/d/1a8xVYLW7ON6jAQoaHGS5U2U93N3u8C0Y49vahNilTsk/edit?usp=sharing"
            target="_blank"
            rel="noreferrer"
          >
            Read the 2-page background
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
          <button type="button" className="button primary" onClick={onContinue}>
            Start with an example
            <span aria-hidden="true">→</span>
          </button>
        </div>
      </section>
    </div>
  );
}
