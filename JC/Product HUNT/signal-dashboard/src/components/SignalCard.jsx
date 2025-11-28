import "./SignalCard.css";

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
      return <span className="status-badge pending">⏳ Pending Enrichment</span>;
    } else if (item.status === 1) {
      return <span className="status-badge analyzing">⏳ Analyzing...</span>;
    }
    return null;
  };

  return (
    <div className="signal-card">
      <div className="signal-header">
        {item.thumbnail_url ? (
          <img src={item.thumbnail_url} alt={item.name} className="avatar-img" />
        ) : (
          <div className="avatar">{item.name[0]}</div>
        )}

        <div className="signal-info">
          <div className="signal-name">{item.name}</div>

          <div className="signal-tags">
            {/* Show status badge while processing */}
            {(item.status === 0 || item.status === 1) && renderStatusBadge()}

            {/* ALWAYS show signal badge if is_signal is true */}
            {item.is_signal && (
              <span className="signal-badge">✓ SIGNAL</span>
            )}

            {/* Show score if available */}
            {item.signal_strength && item.signal_score !== null && (
              <span className={`score-tag ${item.signal_strength}`}>
                Score: {item.signal_score}
              </span>
            )}
          </div>

          <div className="signal-tagline">{item.tagline}</div>

          {item.description && (
            <div className="signal-description">{item.description}</div>
          )}

          <div className="signal-meta">
            {item.created_at && (
              <span className="meta-date"> {formatDate(item.created_at)}</span>
            )}
            <span className="meta-votes"> {item.votes} votes</span>
          </div>
        </div>
      </div>

      {item.topics && item.topics.length > 0 && (
        <div className="topic-list">
          {item.topics.map((t, i) => (
            <span key={i} className="topic-chip">
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}