import React from 'react';

export function ProgressTracker({
  isVisible,
  progressIndicator,
  progressDetails,
  serverType,
  onPlanLoaded,
}) {
  if (!isVisible) return null;

  const details = Array.isArray(progressDetails) ? progressDetails.slice(-6) : [];

  return (
    <div className="px-4">
      <div className="bg-[#2F3136] border border-[#42464D] rounded-xl p-4 text-white">
        <div className="text-sm opacity-80 mb-2">{serverType?.toUpperCase?.() || 'STATUS'}</div>
        <div className="text-base font-medium">{progressIndicator || 'Working...'}</div>
        {details.length > 0 && (
          <ul className="list-disc pl-5 mt-3 space-y-1 text-sm">
            {details.map((d, i) => (
              <li key={i}>{d?.message || d?.type || '...'}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
