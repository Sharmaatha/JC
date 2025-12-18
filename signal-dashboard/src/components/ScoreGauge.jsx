import React from "react";
import "./ScoreGauge.css";

export default function ScoreGauge({ score }) {
  // Determine color based on score
  const getColor = (score) => {
    if (score >= 70) return "#10b981"; // green
    if (score >= 40) return "#f59e0b"; // yellow/orange
    return "#ef4444"; // red
  };

  const color = getColor(score);
  const circumference = 2 * Math.PI * 18; // radius = 18
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="score-gauge">
      <svg width="48" height="48" viewBox="0 0 48 48" className="gauge-svg">
        {/* Background circle */}
        <circle
          cx="24"
          cy="24"
          r="18"
          fill="none"
          stroke="#f1f5f9"
          strokeWidth="4"
        />
        {/* Progress circle */}
        <circle
          cx="24"
          cy="24"
          r="18"
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 24 24)"
          className="gauge-progress"
        />
      </svg>
      <div className="gauge-score" style={{ color }}>
        {score}
      </div>
    </div>
  );
}