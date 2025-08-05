import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';

export default function TestingStuff() {
  const [pulseStates, setPulseStates] = useState({
    llm: false,
    mcp1: false, 
    mcp2: false,
    mcp3: false,
    db1: false,
    db2: false,
    api: false
  });

  useEffect(() => {
    const components = ['llm', 'mcp1', 'mcp2', 'mcp3', 'db1', 'db2', 'api'];
    const intervals = [];

    const triggerRandomPulse = () => {
      const randomComponent = components[Math.floor(Math.random() * components.length)];
      triggerPulse(randomComponent);
    };

    intervals.push(setInterval(() => {
      triggerPulse('llm');
    }, 400 + Math.random() * 300));

    intervals.push(setInterval(() => {
      triggerPulse('mcp' + (Math.floor(Math.random() * 3) + 1));
    }, 600 + Math.random() * 300));

    intervals.push(setInterval(() => {
      const endpoints = ['db1', 'db2', 'api'];
      triggerPulse(endpoints[Math.floor(Math.random() * endpoints.length)]);
    }, 800 + Math.random() * 300));

    intervals.push(setInterval(() => {
      triggerRandomPulse();
    }, 200 + Math.random() * 300));

    return () => intervals.forEach(clearInterval);
  }, []);

  const pulseVariants = {
    pulse: {
      scale: [1, 1.10, 1],
      opacity: [1, 0.9, 1], 
      transition: { duration: 0.3 }
    },
    idle: {
      scale: 1,
      opacity: 1
    }
  };

  const triggerPulse = (component) => {
    setPulseStates(prev => ({ ...prev, [component]: true }));
    setTimeout(() => {
      setPulseStates(prev => ({ ...prev, [component]: false }));
    }, 100);
  };

  

  const circleTransition = {
    duration: 1.125,
    times: [0, 0.33, 0.66, 1],
    repeat: Infinity,
    repeatDelay: 0.375
  };

  const renderCircle = (startX, startY, endX, endY, color, delay = 0) => (
    <motion.circle
      key={`circle-${startX}-${startY}-${endX}-${endY}-${delay}`}
      cx={startX}
      cy={startY}
      r="5"
      fill={color}
      animate={{
        cx: [startX, endX, endX, startX],
        cy: [startY, endY, endY, startY]
      }}
      transition={{
        ...circleTransition,
        delay
      }}
    />
  );

  return (
    <div className="w-full h-full flex items-center justify-center border-1 bg-slate-900 border-slate-700 rounded-2xl">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="135%" height="135%">
        <motion.rect
          x="50"
          y="200"
          width="150"
          height="100"
          rx="10"
          fill="#4f46e5"
          stroke="#ffffff"
          strokeWidth="2"
          variants={pulseVariants}
          animate={pulseStates.llm ? 'pulse' : 'idle'}
        />
        <text x="125" y="235" fontFamily="Arial" fontSize="18" fill="white" textAnchor="middle">LLM</text>
        <text x="125" y="260" fontFamily="Arial" fontSize="18" fill="white" textAnchor="middle">(MCP Host)</text>

        {/* Left to Middle circles */}
        {[0, 0.45, 0.9, 1.35].map((baseDelay, index) => (
          <g key={`left-group-${index}`}>
            {renderCircle(200, 225, 315, 140, "#00ffcc", baseDelay)}
            {renderCircle(200, 250, 315, 250, "#00ffcc", baseDelay + 0.075)}
            {renderCircle(200, 275, 315, 360, "#00ffcc", baseDelay + 0.15)}
          </g>
        ))}

        {/* Middle to Right circles */}
        {[0.3, 0.675, 1.05, 1.425].map((baseDelay, index) => (
          <g key={`right-group-${index}`}>
            {renderCircle(475, 140, 590, 140, "#ffcc00", baseDelay)}
            {renderCircle(475, 250, 590, 250, "#ffcc00", baseDelay + 0.075)}
            {renderCircle(475, 360, 590, 360, "#ffcc00", baseDelay + 0.15)}
          </g>
        ))}

        <motion.rect
          x="325"
          y="100"
          width="150"
          height="80"
          rx="10"
          fill="#3b82f6"
          stroke="#ffffff"
          strokeWidth="2"
          variants={pulseVariants}
          animate={pulseStates.mcp1 ? 'pulse' : 'idle'}
        />
        <text x="400" y="150" fontFamily="Arial" fontSize="16" fill="white" textAnchor="middle">MCP Server 1</text>

        <motion.rect
          x="325"
          y="210"
          width="150"
          height="80"
          rx="10"
          fill="#3b82f6"
          stroke="#ffffff"
          strokeWidth="2"
          variants={pulseVariants}
          animate={pulseStates.mcp2 ? 'pulse' : 'idle'}
        />
        <text x="400" y="260" fontFamily="Arial" fontSize="16" fill="white" textAnchor="middle">MCP Server 2</text>

        <motion.rect
          x="325"
          y="320"
          width="150"
          height="80"
          rx="10"
          fill="#3b82f6"
          stroke="#ffffff"
          strokeWidth="2"
          variants={pulseVariants}
          animate={pulseStates.mcp3 ? 'pulse' : 'idle'}
        />
        <text x="400" y="370" fontFamily="Arial" fontSize="16" fill="white" textAnchor="middle">MCP Server 3</text>

        <motion.rect
          x="600"
          y="100"
          width="150"
          height="80"
          rx="10"
          fill="#10b981"
          stroke="#ffffff"
          strokeWidth="2"
          variants={pulseVariants}
          animate={pulseStates.db1 ? 'pulse' : 'idle'}
        />
        <text x="675" y="150" fontFamily="Arial" fontSize="16" fill="white" textAnchor="middle">Database 1</text>

        <motion.rect
          x="600"
          y="210"
          width="150"
          height="80"
          rx="10"
          fill="#f59e0b"
          stroke="#ffffff"
          strokeWidth="2"
          variants={pulseVariants}
          animate={pulseStates.db2 ? 'pulse' : 'idle'}
        />
        <text x="675" y="260" fontFamily="Arial" fontSize="16" fill="white" textAnchor="middle">Database 2</text>

        <motion.rect
          x="600"
          y="320"
          width="150"
          height="80"
          rx="10"
          fill="#ef4444"
          stroke="#ffffff"
          strokeWidth="2"
          variants={pulseVariants}
          animate={pulseStates.api ? 'pulse' : 'idle'}
        />
        <text x="675" y="370" fontFamily="Arial" fontSize="16" fill="white" textAnchor="middle">Web API</text>

        <line x1="200" y1="225" x2="325" y2="140" stroke="#ffffff" strokeWidth="2"/>
        <line x1="200" y1="250" x2="325" y2="250" stroke="#ffffff" strokeWidth="2"/>
        <line x1="200" y1="275" x2="325" y2="360" stroke="#ffffff" strokeWidth="2"/>

        <line x1="475" y1="140" x2="600" y2="140" stroke="#ffffff" strokeWidth="2"/>
        <line x1="475" y1="250" x2="600" y2="250" stroke="#ffffff" strokeWidth="2"/>
        <line x1="475" y1="360" x2="600" y2="360" stroke="#ffffff" strokeWidth="2"/>

        <text x="400" y="50" fontFamily="Arial" fontSize="40" fontWeight="bold" fill="white" textAnchor="middle">
          Model Context Protocol
        </text>
      </svg>
    </div>
  );
}