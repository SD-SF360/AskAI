import React from "react";

function StatCard({ title, value }) {
  return (
    <div className="statCard">
      <h3>{title}</h3>
      <div className="statValue">{value}</div>
    </div>
  );
}

export default StatCard;