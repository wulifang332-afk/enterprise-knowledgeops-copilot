import { FormEvent, useState } from "react";

import { searchKnowledge, type RetrievalResult, type SearchResponse } from "../api";

type SearchState = {
  response: SearchResponse | null;
  loading: boolean;
  error: string | null;
  emptyQuery: boolean;
  hasSearched: boolean;
};

export function SearchCitationsPage() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<SearchState>({
    response: null,
    loading: false,
    error: null,
    emptyQuery: false,
    hasSearched: false
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();

    if (trimmedQuery.length < 2) {
      setState({
        response: null,
        loading: false,
        error: null,
        emptyQuery: true,
        hasSearched: true
      });
      return;
    }

    setState({
      response: null,
      loading: true,
      error: null,
      emptyQuery: false,
      hasSearched: true
    });

    searchKnowledge(trimmedQuery)
      .then((response) => {
        setState({
          response,
          loading: false,
          error: null,
          emptyQuery: false,
          hasSearched: true
        });
      })
      .catch((error: unknown) => {
        setState({
          response: null,
          loading: false,
          error: messageFor(error),
          emptyQuery: false,
          hasSearched: true
        });
      });
  }

  return (
    <>
      <section className="page-heading" aria-labelledby="search-title">
        <p className="hero__eyebrow">Retrieval transparency</p>
        <h1 className="page-heading__title" id="search-title">
          Search & Citations
        </h1>
        <p className="page-heading__subtitle">
          Search processed enterprise knowledge assets and inspect the exact citations
          returned by the backend retrieval service.
        </p>
      </section>

      <section className="section" aria-labelledby="search-input-title">
        <div className="section__header">
          <h2 className="section__title" id="search-input-title">
            Search Input
          </h2>
          <p className="section__note">Hybrid retrieval, top 5 results, no frontend reranking</p>
        </div>
        <form className="search-form" onSubmit={handleSubmit}>
          <label className="search-form__label" htmlFor="knowledge-query">
            Query
          </label>
          <div className="search-form__row">
            <input
              id="knowledge-query"
              className="search-form__input"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Vendor Payment Request Form"
            />
            <button className="primary-button" type="submit" disabled={state.loading}>
              {state.loading ? "Searching" : "Search"}
            </button>
          </div>
        </form>
      </section>

      <section className="section" aria-labelledby="retrieval-results-title">
        <div className="section__header">
          <h2 className="section__title" id="retrieval-results-title">
            Retrieval Results
          </h2>
          <p className="section__note">Returned chunks with backend citation payloads</p>
        </div>
        <SearchResults state={state} />
      </section>
    </>
  );
}

function SearchResults({ state }: { state: SearchState }) {
  if (!state.hasSearched) {
    return (
      <EmptyPanel
        title="Enter a query"
        description="Run a search to inspect retrieved chunks and citations."
      />
    );
  }

  if (state.emptyQuery) {
    return (
      <EmptyPanel
        title="Empty query"
        description="Enter at least two characters to run citation-backed retrieval."
      />
    );
  }

  if (state.loading) {
    return <EmptyPanel title="Searching" description="Retrieving cited chunks from the local API." />;
  }

  if (state.error) {
    return <EmptyPanel title="Search unavailable" description={state.error} tone="error" />;
  }

  if (!state.response || state.response.results.length === 0) {
    return (
      <EmptyPanel
        title="No results"
        description="The retrieval service returned no chunks for this query."
      />
    );
  }

  return (
    <div className="search-results">
      {state.response.degraded ? (
        <div className="inline-alert">
          Search ran in degraded mode: {state.response.degraded_reasons.join("; ")}
        </div>
      ) : null}
      {state.response.results.map((result) => (
        <ResultCard result={result} key={`${result.rank}-${result.chunk_id}`} />
      ))}
    </div>
  );
}

function ResultCard({ result }: { result: RetrievalResult }) {
  return (
    <article className="result-card">
      <div className="result-card__header">
        <div>
          <p className="result-card__rank">Rank {result.rank}</p>
          <h3>{result.metadata.title}</h3>
        </div>
        <ScoreBadge result={result} />
      </div>

      <dl className="result-meta">
        <div>
          <dt>Source document</dt>
          <dd>{result.doc_id}</dd>
        </div>
        <div>
          <dt>Chunk ID</dt>
          <dd>{result.chunk_id}</dd>
        </div>
        <div>
          <dt>Section</dt>
          <dd>{result.metadata.section_title}</dd>
        </div>
      </dl>

      <section className="citation-block" aria-label={`Citation for ${result.chunk_id}`}>
        <h4>Citation Display</h4>
        <pre>{JSON.stringify(result.citation, null, 2)}</pre>
      </section>

      <details className="result-detail">
        <summary>Inspect result detail</summary>
        <div className="result-detail__grid">
          <section>
            <h4>Chunk text</h4>
            <p className="chunk-text">{result.text}</p>
          </section>
          <section>
            <h4>Citation metadata</h4>
            <pre>{JSON.stringify(result.citation, null, 2)}</pre>
          </section>
          <section>
            <h4>Source information</h4>
            <dl className="source-info">
              <div>
                <dt>Title</dt>
                <dd>{result.metadata.title}</dd>
              </div>
              <div>
                <dt>Source file</dt>
                <dd>{result.metadata.source_file}</dd>
              </div>
              <div>
                <dt>Version</dt>
                <dd>{result.metadata.version}</dd>
              </div>
              <div>
                <dt>Effective date</dt>
                <dd>{result.metadata.effective_date}</dd>
              </div>
            </dl>
          </section>
        </div>
      </details>
    </article>
  );
}

function ScoreBadge({ result }: { result: RetrievalResult }) {
  const score = result.hybrid_score ?? result.bm25_score ?? result.vector_score;
  return (
    <div className="score-badge">
      <span>{score === null ? "N/A" : score.toFixed(3)}</span>
      <small>retrieval score</small>
    </div>
  );
}

function EmptyPanel({
  title,
  description,
  tone = "neutral"
}: {
  title: string;
  description: string;
  tone?: "neutral" | "error";
}) {
  return (
    <div className={`empty-panel empty-panel--${tone}`}>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

function messageFor(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Backend unavailable";
}
