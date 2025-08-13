import React from 'react';

export default function AgenticAccordion({
  isMenuCollapsed,
  serverType,
  handleServerTypeChange,
  isConnecting,
  isLoading,
}) {
  const items = [
    { id: 'rfx', name: 'RFX Database' },
    { id: 'samsara', name: 'Samsara Analysis' },
    { id: 'raw_rfx', name: 'Raw RFX Data' },
  ];

  return (
    <div className="fixed top-0" style={{ left: isMenuCollapsed ? 75 : 300, right: 0, height: 72 }}>
      <div className="flex gap-2 p-3">
        {items.map((item) => (
          <button
            key={item.id}
            onClick={() => handleServerTypeChange?.(item.id)}
            disabled={isConnecting || isLoading}
            className={`px-3 py-2 rounded text-sm border ${
              serverType === item.id
                ? 'border-indigo-500 text-white'
                : 'border-[#42464D] text-[#B9BBBE]'
            }`}
          >
            {item.name}
          </button>
        ))}
      </div>
    </div>
  );
}
