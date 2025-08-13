import React, { useState } from 'react';

export default function Menu({ onCollapse, onReset }) {
  const [collapsed, setCollapsed] = useState(false);

  function toggle() {
    const next = !collapsed;
    setCollapsed(next);
    onCollapse?.(next);
  }

  return (
    <div className="h-screen p-3" style={{ width: collapsed ? 60 : 260 }}>
      <div className="flex items-center justify-between text-white">
        <button onClick={toggle} className="border border-[#42464D] rounded px-2 py-1 text-sm">
          {collapsed ? '>' : '<'}
        </button>
        {!collapsed && (
          <button
            onClick={() => onReset?.()}
            className="border border-[#42464D] rounded px-2 py-1 text-sm"
          >
            Reset
          </button>
        )}
      </div>
    </div>
  );
}
