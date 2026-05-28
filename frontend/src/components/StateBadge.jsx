import React from 'react';

export function StateBadge({ label, value }) {
  return (
    <div className="px-3 py-2 rounded-lg bg-dark-200 border border-dark-300">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-sm text-white font-medium">{value}</p>
    </div>
  );
}
