import { useEffect, useMemo, useState } from 'react'
import './App.css'

const apiBaseUrl = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

function App() {
  const [products, setProducts] = useState([])
  const [query, setQuery] = useState('')
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    async function loadProducts() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/products`)
        const payload = await response.json()

        if (!active) {
          return
        }

        const nextProducts = payload.products ?? []
        setProducts(nextProducts)

        if (nextProducts.length > 0) {
          setQuery(nextProducts[0])

          try {
            const summaryResponse = await fetch(
              `${apiBaseUrl}/api/product-feedback?product=${encodeURIComponent(nextProducts[0])}`,
            )
            const summaryPayload = await summaryResponse.json()

            if (!summaryResponse.ok) {
              throw new Error(summaryPayload.error ?? 'Failed to fetch product feedback.')
            }

            setSummary(summaryPayload)
          } catch {
            if (active) {
              setError('Unable to load the initial product summary.')
            }
          }
        }
      } catch {
        if (active) {
          setError('Unable to load products from the backend.')
        }
      }
    }

    loadProducts()

    return () => {
      active = false
    }
  }, [])

  const loadSummary = async (productName) => {
    const trimmedProduct = productName.trim()

    if (!trimmedProduct) {
      setError('Type a product name first.')
      return
    }

    setLoading(true)
    setError('')

    try {
      const response = await fetch(
        `${apiBaseUrl}/api/product-feedback?product=${encodeURIComponent(trimmedProduct)}`,
      )
      const payload = await response.json()

      if (!response.ok) {
        throw new Error(payload.error ?? 'Failed to fetch product feedback.')
      }

      setSummary(payload)
    } catch (fetchError) {
      setSummary(null)
      setError(fetchError.message)
    } finally {
      setLoading(false)
    }
  }

  const suggestions = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()

    if (!normalizedQuery) {
      return products.slice(0, 8)
    }

    return products.filter((productName) =>
      productName.toLowerCase().includes(normalizedQuery),
    ).slice(0, 8)
  }, [products, query])

  const handleSubmit = (event) => {
    event.preventDefault()
    loadSummary(query)
  }

  const handleSuggestionClick = (productName) => {
    setQuery(productName)
    loadSummary(productName)
  }

  const averageRating = summary?.average_rating?.toFixed(1) ?? '0.0'
  const positivePercent = summary?.positive_percent?.toFixed(0) ?? '0'
  const negativePercent = summary?.negative_percent?.toFixed(0) ?? '0'
  const reviewCount = summary?.review_count ?? 0
  const modelName = summary?.best_model ?? 'Logistic Regression'

  return (
    <main className="dashboard-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Notebook to dashboard</p>
          <h1>Product Feedback Intelligence</h1>
          <p className="hero-text">
            Type a product name and the app will pull live feedback from the backend,
            run the notebook-trained sentiment model, and summarize the product response.
          </p>

          <div className="hero-stats">
            <div>
              <span>Best model</span>
              <strong>{modelName}</strong>
            </div>
            <div>
              <span>Matching products</span>
              <strong>{summary?.matched_products?.length ?? 0}</strong>
            </div>
            <div>
              <span>Reviews analyzed</span>
              <strong>{reviewCount}</strong>
            </div>
          </div>
        </div>
        <form className="search-panel" onSubmit={handleSubmit}>
          <label htmlFor="product-search">Select a product</label>
          <div className="search-row">
            <input
              id="product-search"
              list="product-options"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Type a product name"
            />
            <button type="submit" disabled={loading}>
              {loading ? 'Analyzing...' : 'Analyze'}
            </button>
          </div>
          <datalist id="product-options">
            {products.map((productName) => (
              <option key={productName} value={productName} />
            ))}
          </datalist>
          <div className="suggestions">
            {suggestions.map((productName) => (
              <button
                key={productName}
                type="button"
                className="suggestion-chip"
                onClick={() => handleSuggestionClick(productName)}
              >
                {productName}
              </button>
            ))}
          </div>
          {error ? <p className="error-banner">{error}</p> : null}
        </form>
      </section>

      <section className="metrics-grid">
        <article className="metric-card accent-green">
          <span>Average rating</span>
          <strong>{averageRating} / 5</strong>
          <p>Based on the matched reviews for the selected product.</p>
        </article>
        <article className="metric-card accent-blue">
          <span>Positive feedback</span>
          <strong>{positivePercent}%</strong>
          <p>Predicted by the notebook-trained sentiment model.</p>
        </article>
        <article className="metric-card accent-red">
          <span>Negative feedback</span>
          <strong>{negativePercent}%</strong>
          <p>Reviews classified as negative by the model.</p>
        </article>
        <article className="metric-card accent-gold">
          <span>Total reviews</span>
          <strong>{reviewCount}</strong>
          <p>Rows matched from the cleaned dataset.</p>
        </article>
      </section>

      <section className="analysis-grid">
        <article className="feedback-card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Overview</p>
              <h2>{summary?.product_name ?? 'Search a product to begin'}</h2>
            </div>
            {summary?.matched ? (
              <span className="model-badge">{summary.best_model}</span>
            ) : null}
          </div>

          {summary?.matched ? (
            <>
              <div className="progress-stack">
                <div className="progress-row">
                  <div>
                    <span>Positive</span>
                    <strong>{positivePercent}%</strong>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill positive" style={{ width: `${positivePercent}%` }} />
                  </div>
                </div>
                <div className="progress-row">
                  <div>
                    <span>Negative</span>
                    <strong>{negativePercent}%</strong>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill negative" style={{ width: `${negativePercent}%` }} />
                  </div>
                </div>
              </div>

              <div className="model-table">
                <h3>Model comparison</h3>
                <div className="model-table-head">
                  <span>Model</span>
                  <span>Accuracy</span>
                  <span>F1</span>
                </div>
                {summary.model_comparison?.map((row) => (
                  <div className="model-table-row" key={row.Model}>
                    <span>{row.Model}</span>
                    <span>{Number(row.Accuracy).toFixed(3)}</span>
                    <span>{Number(row['F1 Score']).toFixed(3)}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="empty-state">
              Enter a product name to see live sentiment predictions, average rating, and review snippets.
            </p>
          )}
        </article>

        <aside className="sidebar-card">
          <div className="section-head compact">
            <div>
              <p className="eyebrow">Matched products</p>
              <h2>{summary?.matched_products?.length ?? 0}</h2>
            </div>
          </div>

          <div className="chip-list">
            {(summary?.matched_products ?? suggestions).map((productName) => (
              <button
                key={productName}
                type="button"
                className="chip"
                onClick={() => handleSuggestionClick(productName)}
              >
                {productName}
              </button>
            ))}
          </div>

          <div className="category-breakdown">
            <h3>Category mix</h3>
            {summary?.category_breakdown?.length ? (
              summary.category_breakdown.map((item) => (
                <div className="category-row" key={item.category}>
                  <span>{item.category}</span>
                  <strong>{item.size}</strong>
                </div>
              ))
            ) : (
              <p className="muted">No category data yet.</p>
            )}
          </div>
        </aside>
      </section>

      <section className="reviews-section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Customer reviews</p>
            <h2>Model-based feedback highlights</h2>
          </div>
        </div>

        <div className="reviews-list">
          {(summary?.top_reviews ?? []).map((review, index) => (
            <article className="review-card" key={`${review.review_text}-${index}`}>
              <div className="review-card-head">
                <div>
                  <p className="review-rating">{review.rating} / 5 rating</p>
                  <h3>{review.predicted_sentiment}</h3>
                </div>
                <span
                  className={
                    review.predicted_sentiment === 'Positive'
                      ? 'sentiment-chip positive'
                      : 'sentiment-chip negative'
                  }
                >
                  {review.confidence}% confidence
                </span>
              </div>
              <p className="review-text">{review.review_text}</p>
              <div className="review-meta">
                <span>Age {review.reviewer_age}</span>
                <span>Helpful {review.helpful_votes}</span>
              </div>
            </article>
          ))}

          {!summary?.top_reviews?.length ? (
            <article className="review-card placeholder-card">
              <h3>No reviews yet</h3>
              <p>Search for a product to populate the feedback dashboard.</p>
            </article>
          ) : null}
        </div>
      </section>
    </main>
  )
}

export default App
