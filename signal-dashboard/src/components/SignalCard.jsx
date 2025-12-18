import React from "react";
import "./SignalCard.css";
import ScoreGauge from "./ScoreGauge";

// Skeleton loading component
export function SkeletonCard() {
  return (
    <article className="signal-card skeleton" role="article">
      <div className="signal-header">
        <div className="avatar skeleton-avatar" aria-hidden></div>

        <div className="signal-info">
          <div className="signal-name skeleton-text skeleton-title"></div>

          <div className="signal-tags">
            <span className="skeleton-badge"></span>
            <span className="skeleton-badge skeleton-score"></span>
          </div>

          <div className="signal-tagline skeleton-text"></div>
          <div className="signal-description skeleton-text"></div>

          <div className="signal-meta" aria-hidden>
            <span className="meta-date skeleton-text skeleton-meta"></span>
            <span className="meta-votes skeleton-text skeleton-meta"></span>
          </div>
        </div>
      </div>

      <div className="topic-list" aria-label="topics">
        <span className="topic-chip skeleton-chip"></span>
        <span className="topic-chip skeleton-chip"></span>
        <span className="topic-chip skeleton-chip"></span>
        <span className="topic-chip skeleton-chip"></span>
      </div>
    </article>
  );
}

export default function SignalCard({ item }) {
  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const renderStatusBadge = () => {
    if (item.status === 0) {
      return <span className="status-badge pending">Pending</span>;
    } else if (item.status === 1) {
      return <span className="status-badge analyzing">Analyzing</span>;
    }
    return null;
  };

  return (
    <article className="signal-card" role="article" aria-labelledby={`signal-${item.id}`}>
      <div className="signal-header">
        {item.thumbnail_url ? (
          <img
            src={item.thumbnail_url}
            alt={item.name}
            className="avatar-img"
            width={68}
            height={68}
          />
        ) : (
          <div className="avatar" aria-hidden>
            {item.name ? item.name[0].toUpperCase() : "S"}
          </div>
        )}

        <div className="signal-info">
          <div id={`signal-${item.id}`} className="signal-name">{item.name}</div>

          <div className="signal-tags">
            {/* status */}
            {(item.status === 0 || item.status === 1) && renderStatusBadge()}

            {/* signal badge */}
            {item.is_signal && <span className="signal-badge">SIGNAL</span>}

            {/* NEW: Score Gauge instead of text */}
            {item.signal_score !== null && (
              <div className="score-gauge-wrapper">
                <ScoreGauge score={item.signal_score} />
                <span className="score-strength-label">
                  {item.signal_strength === "strong" ? "Strong" : 
                   item.signal_strength === "moderate" ? "Moderate" : 
                   item.signal_strength === "weak" ? "Weak" : ""}
                </span>
              </div>
            )}
          </div>

          {item.tagline && <div className="signal-tagline">{item.tagline}</div>}

          {item.description && (
            <div className="signal-description">{item.description}</div>
          )}

          <div className="signal-meta" aria-hidden>
            {item.created_at && <span className="meta-date">{formatDate(item.created_at)}</span>}
            <span className="meta-votes">{item.votes} votes</span>
          </div>
        </div>
      </div>

      {item.topics && item.topics.length > 0 && (
        <div className="topic-list" aria-label="topics">
          {item.topics.map((t, i) => (
            <span key={i} className="topic-chip">
              {t}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}