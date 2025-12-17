import { useEffect, useState, useRef } from "react";
import { getSignals, checkDateExists, scrapeDate } from "./api";
import SignalCard, { SkeletonCard } from "./components/SignalCard";
import "./App.css";

interface SignalProduct {
  id: number;
  name: string;
  company_name?: string;
  tagline: string;
  description: string;
  thumbnail_url?: string;
  topics: string[];
  votes: number;
  signal_score: number | null;
  signal_strength: string | null;
  is_signal: boolean;
  created_at: string;
  launch_date?: string;
  status: number;
}

export default function App() {
  const [signals, setSignals] = useState<SignalProduct[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState("");
  const [scoreFilter, setScoreFilter] = useState("all");
  const [signalFilter, setSignalFilter] = useState("all");
  const [sortBy, setSortBy] = useState("none");
  const [viewFilterDate, setViewFilterDate] = useState("");

  // NEW: Unlimited scrape toggle
  const [unlimitedScrape, setUnlimitedScrape] = useState(false);

  // Infinite scroll
  const [displayCount, setDisplayCount] = useState(10);
  const observerTarget = useRef<HTMLDivElement>(null);

  // Scraping state
  const [scraping, setScraping] = useState(false);
  const [scrapeError, setScrapeError] = useState<string | null>(null);

  // Polling state
  const [isPolling, setIsPolling] = useState(false);
  const pollingIntervalRef = useRef<number | null>(null);

  // Loading timeout to prevent stuck loading states
  const loadingTimeoutRef = useRef<number | null>(null);

  const load = async (dateFilter?: string) => {
    try {
      if (!isPolling) {
        setLoading(true);
      }

      // Set a timeout to prevent infinite loading (30 seconds)
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
      }
      loadingTimeoutRef.current = window.setTimeout(() => {
        console.warn("Loading timeout reached, forcing loading state to false");
        setLoading(false);
        setScraping(false);
      }, 30000);

      const res = await getSignals(dateFilter);
      const data = Array.isArray(res.data) ? res.data : res.data.data;
      setSignals(data ?? []);
      setLoading(false);

      // Clear the timeout since loading completed successfully
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
        loadingTimeoutRef.current = null;
      }
    } catch (error) {
      console.error("Error loading signals:", error);
      setLoading(false);
      // Clear timeout on error
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
        loadingTimeoutRef.current = null;
      }
    }
  };

  const stopPolling = () => {
    setIsPolling(false);
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  };

  const checkIfProcessingComplete = (products: SignalProduct[]) => {
    if (products.length === 0) return true;
    return products.every((p) => p.status === 2);
  };

  const handleViewFilterDateChange = async (pickedDate: string) => {
    if (!pickedDate) {
      setViewFilterDate("");
      stopPolling();
      setDisplayCount(10);
      setLoading(true); // Ensure loading state is set
      await load();
      return;
    }

    setViewFilterDate(pickedDate);
    setScrapeError(null);
    setDisplayCount(10);
    setLoading(true); // Set loading when starting date check

    try {
      const checkRes = await checkDateExists(pickedDate);
      console.log("checkDateExists response:", checkRes.data);

      if (!checkRes.data.exists) {
        setScraping(true);
        setScrapeError(null);
        setLoading(false); // Clear general loading when scraping starts

        try {
          // Pass unlimited flag to scrapeDate
          await scrapeDate(pickedDate, unlimitedScrape);
          setLoading(true); // Set loading for final data load
          await load(pickedDate);
          setScraping(false);
          setLoading(false);
        } catch (error: any) {
          setScraping(false);
          setLoading(false); // Ensure loading is cleared on error
          const errorMsg =
            error.response?.data?.detail || "Scraping failed. Please try again.";
          setScrapeError(errorMsg);
        }
      } else {
        setLoading(true); // Ensure loading is set before load call
        await load(pickedDate);
        setLoading(false);
      }
    } catch (error) {
      console.error("Error checking date:", error);
      setLoading(false); // Clear loading on error
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (isPolling && checkIfProcessingComplete(signals)) {
      stopPolling();
    }
  }, [signals, isPolling]);

  useEffect(() => {
    return () => {
      stopPolling();
      // Clear loading timeout on unmount
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
      }
    };
  }, []);

  const getFilteredProducts = () => {
    return signals.filter((item) => {
      const s = search.toLowerCase();

      const matchesSearch =
        item.name.toLowerCase().includes(s) ||
        item.company_name?.toLowerCase().includes(s) ||
        item.tagline?.toLowerCase().includes(s) ||
        item.description?.toLowerCase().includes(s) ||
        item.topics.some((t) => t.toLowerCase().includes(s));

      const strength = item.signal_strength ?? "none";

      const matchesScore =
        scoreFilter === "all"
          ? true
          : scoreFilter === "strong"
          ? strength === "strong"
          : scoreFilter === "moderate"
          ? strength === "moderate"
          : scoreFilter === "weak"
          ? strength === "weak"
          : scoreFilter === "80plus"
          ? (item.signal_score ?? 0) >= 80
          : scoreFilter === "60plus"
          ? (item.signal_score ?? 0) >= 60
          : true;

      const matchesSignal =
        signalFilter === "all"
          ? true
          : signalFilter === "signal"
          ? item.is_signal === true
          : item.is_signal === false;

      const matchesViewDate = viewFilterDate
        ? item.launch_date === viewFilterDate
        : true;

      return matchesSearch && matchesScore && matchesSignal && matchesViewDate;
    });
  };

  const filtered = getFilteredProducts();

  const safeScore = (n: number | null) => (typeof n === "number" ? n : 0);

  let sorted = [...filtered];

  if (sortBy === "score_desc") {
    sorted.sort((a, b) => safeScore(b.signal_score) - safeScore(a.signal_score));
  } else if (sortBy === "score_asc") {
    sorted.sort((a, b) => safeScore(a.signal_score) - safeScore(b.signal_score));
  } else if (sortBy === "name_asc") {
    sorted.sort((a, b) => a.name.localeCompare(b.name));
  } else if (sortBy === "name_desc") {
    sorted.sort((a, b) => b.name.localeCompare(a.name));
  }

  const displayed = sorted.slice(0, displayCount);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && displayed.length < sorted.length) {
          setDisplayCount((prev) => prev + 10);
        }
      },
      { threshold: 0.1, rootMargin: "100px" }
    );

    const currentTarget = observerTarget.current;
    if (currentTarget) {
      observer.observe(currentTarget);
    }

    return () => {
      if (currentTarget) observer.unobserve(currentTarget);
    };
  }, [displayed.length, sorted.length]);

  function resetFilters() {
    setSearch("");
    setScoreFilter("all");
    setSignalFilter("all");
    setSortBy("none");
    setViewFilterDate("");
    setScrapeError(null);
    setDisplayCount(10);
    setUnlimitedScrape(false); // Reset unlimited toggle
    stopPolling();
    load();
  }

  // Render skeleton cards during loading
  const renderSkeletonCards = () => {
    const skeletonCards = [];
    for (let i = 0; i < 10; i++) { // Show 10 skeleton cards
      skeletonCards.push(<SkeletonCard key={`skeleton-${i}`} />);
    }
    return skeletonCards;
  };

  if (loading) {
    return (
      <div className="layout">
        <div className="content">
          <div className="header-section">
            <h1>Startup Signal Dashboard</h1>
            <p className="subtitle">Track and analyze emerging startup signals</p>
          </div>

          {/* Products wrapper - all controls + grid inside constrained width */}
          <div className="content-inner">
            {/* ======= CLEAN TOP SEARCH BAR ======= */}
            <div className="top-search-container">
              <div className="top-search-box">
                <svg
                  className="search-icon"
                  width="16"
                  height="16"
                  viewBox="0 0 20 20"
                >
                  <path
                    d="M9 17A8 8 0 1 0 9 1a8 8 0 0 0 0 16zM18.5 18.5l-4-4"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    fill="none"
                  />
                </svg>

                <input
                  type="text"
                  placeholder="Search products..."
                  className="top-search-input skeleton-input"
                  disabled
                />
              </div>
            </div>

            {/* ======= FILTER TOOLBAR ======= */}
            <div className="filter-toolbar">
              <div className="filter-col">
                <label>Scrape Mode</label>
                <label className="toggle-switch">
                  <input type="checkbox" disabled />
                  <span className="toggle-label">
                    🔓 Unlimited
                  </span>
                </label>
              </div>

              <div className="filter-col">
                <label>Date</label>
                <input
                  type="date"
                  className="filter-input skeleton-input"
                  disabled
                />
              </div>

              <div className="filter-col">
                <label>Type</label>
                <select className="filter-input skeleton-input" disabled>
                  <option>All</option>
                </select>
              </div>

              <div className="filter-col">
                <label>Score</label>
                <select className="filter-input skeleton-input" disabled>
                  <option>All</option>
                </select>
              </div>

              <div className="filter-col">
                <label>Sort</label>
                <select className="filter-input skeleton-input" disabled>
                  <option>Default</option>
                </select>
              </div>

              <div className="filter-col">
                <label>&nbsp;</label>
                <button className="reset-btn-final" disabled>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </div>
            </div>

            {/* Results display count */}
            <div className="results-info">
              <span className="skeleton-text skeleton-results">Loading products...</span>
            </div>

            {/* Skeleton cards grid */}
            <div className="signals-grid">
              {renderSkeletonCards()}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="layout">
      <div className="content">
        <div className="header-section">
          <h1>Startup Signal Dashboard</h1>
          <p className="subtitle">Track and analyze emerging startup signals</p>
        </div>

        {/* Status Notifications */}
        {scraping && (
          <div className="alert alert-warning">
            <span className="alert-icon">⏳</span>
            <div>
              <strong>Scraping in progress...</strong>
              <p>
                {unlimitedScrape
                  ? "Fetching ALL products for this date. This may take 5-15 minutes."
                  : "Fetching Product Hunt data. This may take 2-5 minutes."}
              </p>
            </div>
          </div>
        )}

        {scrapeError && (
          <div className="alert alert-error">
            <span className="alert-icon">⚠️</span>
            <div>
              <strong>Error</strong>
              <p>{scrapeError}</p>
            </div>
          </div>
        )}

        {/* Products wrapper - all controls + grid inside constrained width */}
        <div className="content-inner">
          {/* ======= CLEAN TOP SEARCH BAR ======= */}
          <div className="top-search-container">
            <div className="top-search-box">
              <svg
                className="search-icon"
                width="16"
                height="16"
                viewBox="0 0 20 20"
              >
                <path
                  d="M9 17A8 8 0 1 0 9 1a8 8 0 0 0 0 16zM18.5 18.5l-4-4"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  fill="none"
                />
              </svg>

              <input
                type="text"
                placeholder="Search products..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="top-search-input"
              />

              {search && (
                <button
                  className="clear-top-search"
                  onClick={() => setSearch("")}
                  aria-label="Clear search"
                >
                  ✕
                </button>
              )}
            </div>
          </div>

          {/* ======= FILTER TOOLBAR ======= */}
          <div className="filter-toolbar">
            {/* NEW: Unlimited Scrape Toggle */}
            <div className="filter-col">
              <label>Scrape Mode</label>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={unlimitedScrape}
                  onChange={(e) => setUnlimitedScrape(e.target.checked)}
                />
                <span className="toggle-label">
                  {unlimitedScrape ? "🔓 Unlimited" : "🔒 Limited (50)"}
                </span>
              </label>
            </div>

            <div className="filter-col">
              <label>Date</label>
              <input
                type="date"
                value={viewFilterDate}
                onChange={(e) => handleViewFilterDateChange(e.target.value)}
                className="filter-input"
              />
            </div>

            <div className="filter-col">
              <label>Type</label>
              <select
                className="filter-input"
                value={signalFilter}
                onChange={(e) => setSignalFilter(e.target.value)}
              >
                <option value="all">All</option>
                <option value="signal">Signal</option>
                <option value="not-signal">Not Signal</option>
              </select>
            </div>

            <div className="filter-col">
              <label>Score</label>
              <select
                className="filter-input"
                value={scoreFilter}
                onChange={(e) => setScoreFilter(e.target.value)}
              >
                <option value="all">All</option>
                <option value="strong">Strong</option>
                <option value="moderate">Moderate</option>
                <option value="weak">Weak</option>
                <option value="80plus">≥ 80</option>
                <option value="60plus">≥ 60</option>
              </select>
            </div>

            <div className="filter-col">
              <label>Sort</label>
              <select
                className="filter-input"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                <option value="none">Default</option>
                <option value="score_desc">High → Low</option>
                <option value="score_asc">Low → High</option>
                <option value="name_asc">A → Z</option>
                <option value="name_desc">Z → A</option>
              </select>
            </div>

            <div className="filter-col">
              <label>&nbsp;</label>
              <button
                className="reset-btn-final reset-tooltip"
                onClick={resetFilters}
                aria-label="Reset filters"
                data-tooltip="Reset filters"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          </div>

          {/* Results display count */}
          <div className="results-info">
            <span>Showing {displayed.length} products</span>
          </div>
          {displayed.length === 0 ? (
            <div className="empty-state">
              <h3>No signals found</h3>
              <p>Try adjusting your filters or search query</p>
            </div>
          ) : (
            <div className="signals-grid">
              {displayed.map((s) => (
                <SignalCard key={s.id} item={s} />
              ))}

              {displayed.length < sorted.length && (
                <div ref={observerTarget} className="loading-more">
                  <div className="spinner-small"></div>
                  <span>Loading more products...</span>
                </div>
              )}
            </div>
          )}
        </div>
        {/* END content-inner */}
      </div>
    </div>
  );
}