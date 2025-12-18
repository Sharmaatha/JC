import React from "react";
import "./DashboardStats.css";

export default function DashboardStats({ signals }) {
  // Calculate statistics
  const totalSignals = signals.filter(s => s.is_signal).length;
  const totalProducts = signals.length;
  
  const scores = signals
    .filter(s => s.signal_score !== null)
    .map(s => s.signal_score);
  
  const avgScore = scores.length > 0
    ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
    : 0;

  // Count processed items (status 2)
  const processedCount = signals.filter(s => s.status === 2).length;
  const pendingCount = totalProducts - processedCount;

  const stats = [
    {
      label: "Signals",
      value: totalSignals,
      subtitle: `${totalProducts} total`,
      icon: "🎯",
      iconBg: "#dbeafe",
      iconColor: "#2563eb"
    },
    {
      label: "Avg Score",
      value: avgScore,
      subtitle: "out of 100",
      icon: "📊",
      iconBg: avgScore >= 70 ? "#d1fae5" : avgScore >= 40 ? "#fef3c7" : "#fee2e2",
      iconColor: avgScore >= 70 ? "#059669" : avgScore >= 40 ? "#d97706" : "#dc2626"
    },
    {
      label: "Processed",
      value: processedCount,
      subtitle: `${totalProducts} total`,
      icon: "✓",
      iconBg: "#d1fae5",
      iconColor: "#059669"
    },
    {
      label: "Pending",
      value: pendingCount,
      subtitle: pendingCount === 1 ? "item" : "items",
      icon: "⏳",
      iconBg: "#e9d5ff",
      iconColor: "#7c3aed"
    }
  ];

  return (
    <div className="dashboard-stats-container">
      {stats.map((stat, idx) => (
        <div key={idx} className="stat-card-new">
          <div 
            className="stat-icon-new" 
            style={{ 
              background: stat.iconBg,
              color: stat.iconColor 
            }}
          >
            {stat.icon}
          </div>
          <div className="stat-info">
            <div className="stat-label-new">{stat.label}</div>
            <div className="stat-value-new">{stat.value}</div>
            <div className="stat-subtitle-new">{stat.subtitle}</div>
          </div>
        </div>
      ))}
    </div>
  );
}