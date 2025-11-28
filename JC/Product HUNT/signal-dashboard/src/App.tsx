import { useEffect, useState, useRef } from "react";
import { getSignals, checkDateExists, scrapeDate } from "./api";
import Sidebar from "./layout/Sidebar";
import SignalCard from "./components/SignalCard";
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
  const [selectedDate, setSelectedDate] = useState("");
  const [viewFilterDate, setViewFilterDate] = useState("");

  // Infinite scroll
  const [displayCount, setDisplayCount] = useState(10);
  const observerTarget = useRef<HTMLDivElement>(null);

  // Scraping state
  const [scraping, setScraping] = useState(false);
  const [scrapeError, setScrapeError] = useState<string | null>(null);

  // Polling state
  const [isPolling, setIsPolling] = useState(false);
  const pollingIntervalRef = useRef<number | null>(null);

  const load = async (dateFilter?: string) => {
    try {
      if (!isPolling) {
        setLoading(true);
      }
      const res = await getSignals(dateFilter);
      const data = Array.isArray(res.data) ? res.data : res.data.data;
      setSignals(data ?? []);
      setLoading(false);
    } catch (error) {
      console.error("Error loading signals:", error);
      setLoading(false);
    }
  };

  const startPolling = (dateFilter?: string) => {
    setIsPolling(true);
    pollingIntervalRef.current = window.setInterval(() => {
      load(dateFilter);
    }, 2000);
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

  const handleDatePickerChange = async (pickedDate: string) => {
    if (!pickedDate) {
      setSelectedDate("");
      stopPolling();
      setDisplayCount(10);
      await load();
      return;
    }

    setSelectedDate(pickedDate);
    setScrapeError(null);
    setDisplayCount(10);

    try {
      const checkRes = await checkDateExists(pickedDate);

      if (!checkRes.data.exists) {
        setScraping(true);
        setScrapeError(null);

        try {
          await scrapeDate(pickedDate);
          await load(pickedDate);
          setScraping(false);
          startPolling(pickedDate);
        } catch (error: any) {
          setScraping(false);
          const errorMsg =
            error.response?.data?.detail || "Scraping failed. Please try again.";
          setScrapeError(errorMsg);
          stopPolling();
        }
      } else {
        await load(pickedDate);
        const res = await getSignals(pickedDate);
        const data = Array.isArray(res.data) ? res.data : res.data.data;
        if (!checkIfProcessingComplete(data)) {
          startPolling(pickedDate);
        }
      }
    } catch (error) {
      console.error("Error checking date:", error);
    }
  };

  const handleViewFilterDateChange = (pickedDate: string) => {
    setViewFilterDate(pickedDate);
    setDisplayCount(10);
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (isPolling && checkIfProcessingComplete(signals)) {
      stopPolling();
      console.log("All products processed, polling stopped");
    }
  }, [signals, isPolling]);

  useEffect(() => {
    return () => {
      stopPolling();
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
      if (currentTarget) {
        observer.unobserve(currentTarget);
      }
    };
  }, [displayed.length, sorted.length]);

  const resetFilters = () => {
    setSearch("");
    setScoreFilter("all");
    setSignalFilter("all");
    setSortBy("none");
    setSelectedDate("");
    setViewFilterDate(""); 
    setScrapeError(null);
    setDisplayCount(10);
    stopPolling();
    load();
  };

  if (loading) {
    return (
      <div className="layout">
        <Sidebar />
        <div className="content">
          <div className="loading">Loading products...</div>
        </div>
      </div>
    );
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const options: Intl.DateTimeFormatOptions = {
      month: "short",
      day: "numeric",
      year: "numeric",
    };
    return date.toLocaleDateString("en-US", options);
  };

  return (
    <div className="layout">
      <Sidebar />
      <div className="content">
        <h1>Startup Signal Dashboard</h1>

        {scraping && (
          <div
            style={{
              padding: "15px",
              background: "#fff3cd",
              border: "1px solid #ffc107",
              borderRadius: "6px",
              marginBottom: "20px",
              fontWeight: 600,
            }}
          >
            Scraping Product Hunt data... This may take 2-5 minutes. Please wait.
          </div>
        )}

        {isPolling && (
          <div
            style={{
              padding: "15px",
              background: "#d1ecf1",
              border: "1px solid #0c5460",
              borderRadius: "6px",
              marginBottom: "20px",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: "10px",
            }}
          >
            <span>⏳ Processing data in background... Auto-refreshing every 5 seconds</span>
          </div>
        )}

        {scrapeError && (
          <div
            style={{
              padding: "15px",
              background: "#f8d7da",
              border: "1px solid #dc3545",
              borderRadius: "6px",
              marginBottom: "20px",
              color: "#721c24",
            }}
          >
            {scrapeError}
          </div>
        )}

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "15px",
            marginBottom: "20px",
          }}
        >
          <input
            type="text"
            placeholder="Search signals..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              padding: "10px",
              borderRadius: "6px",
              border: "1px solid #ccc",
              width: "100%",
            }}
          />

          {/* Scrape Trigger Date Picker */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <label style={{ fontWeight: 600, whiteSpace: "nowrap" }}>
              Scrape New Date:
            </label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => handleDatePickerChange(e.target.value)}
              disabled={scraping}
              max={new Date().toISOString().split("T")[0]}
              style={{
                padding: "10px",
                borderRadius: "6px",
                border: "1px solid #ccc",
                opacity: scraping ? 0.6 : 1,
                cursor: scraping ? "not-allowed" : "pointer",
                minWidth: "160px",
              }}
            />
            {selectedDate && (
              <button
                onClick={() => handleDatePickerChange("")}
                style={{
                  padding: "10px",
                  borderRadius: "6px",
                  border: "1px solid #ccc",
                  background: "white",
                  cursor: "pointer",
                }}
                title="Clear date"
              >
                ✕
              </button>
            )}
          </div>

          {/* NEW: View-Only Date Filter */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <label style={{ fontWeight: 600, whiteSpace: "nowrap" }}>
              Filter by Date:
            </label>
            <input
              type="date"
              value={viewFilterDate}
              onChange={(e) => handleViewFilterDateChange(e.target.value)}
              max={new Date().toISOString().split("T")[0]}
              style={{
                padding: "10px",
                borderRadius: "6px",
                border: "1px solid #ccc",
                minWidth: "160px",
              }}
            />
            {viewFilterDate && (
              <button
                onClick={() => handleViewFilterDateChange("")}
                style={{
                  padding: "10px",
                  borderRadius: "6px",
                  border: "1px solid #ccc",
                  background: "white",
                  cursor: "pointer",
                }}
                title="Clear date filter"
              >
                ✕
              </button>
            )}
          </div>

          <div style={{ display: "flex", gap: "15px", flexWrap: "wrap" }}>
            <select
              value={signalFilter}
              onChange={(e) => setSignalFilter(e.target.value)}
              style={{
                padding: "10px",
                borderRadius: "6px",
                border: "1px solid #ccc",
              }}
            >
              <option value="all">All Signals</option>
              <option value="signal">Signal</option>
              <option value="not-signal">Not Signal</option>
            </select>

            <select
              value={scoreFilter}
              onChange={(e) => setScoreFilter(e.target.value)}
              style={{
                padding: "10px",
                borderRadius: "6px",
                border: "1px solid #ccc",
              }}
            >
              <option value="all">All Scores</option>
              <option value="strong">Strong</option>
              <option value="moderate">Moderate</option>
              <option value="weak">Weak</option>
              <option value="80plus">Score ≥ 80</option>
              <option value="60plus">Score ≥ 60</option>
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              style={{
                padding: "10px",
                borderRadius: "6px",
                border: "1px solid #ccc",
              }}
            >
              <option value="none">Sort</option>
              <option value="score_desc">Score: High → Low</option>
              <option value="score_asc">Score: Low → High</option>
              <option value="name_asc">Name: A → Z</option>
              <option value="name_desc">Name: Z → A</option>
            </select>

            <button
              onClick={resetFilters}
              style={{
                padding: "10px 16px",
                borderRadius: "6px",
                border: "none",
                background: "#ddd",
                cursor: "pointer",
              }}
            >
              Reset All
            </button>
          </div>
        </div>

        <p style={{ color: "#666", marginBottom: "20px" }}>
          Showing {displayed.length} products
          {viewFilterDate && ` • Launch Date: ${formatDate(viewFilterDate)}`}
        </p>

        {displayed.length === 0 ? (
          <p>No matching signals found</p>
        ) : (
          <>
            {displayed.map((s) => (
              <SignalCard key={s.id} item={s} />
            ))}

            {displayed.length < sorted.length && (
              <div
                ref={observerTarget}
                style={{
                  padding: "20px",
                  textAlign: "center",
                  color: "#999",
                  minHeight: "50px",
                }}
              >
                Loading more products...
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}