import React from 'react';
import ReactMarkdown from 'react-markdown';

// UI utilities for chat interface and markdown parsing 

export function scrollToBottom(messagesEndRef) {
  setTimeout(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: "smooth",
        block: "end"
      });
    }
  }, 100);
}

export function handleTyping(typingTimeoutRef, setGlowIntensity) {
  if (typingTimeoutRef.current) {
    clearTimeout(typingTimeoutRef.current);
  }
  
  setGlowIntensity(20);
  
  typingTimeoutRef.current = setTimeout(() => {
    const fadeOutInterval = setInterval(() => {
      setGlowIntensity(prev => {
        if (prev <= 0.5) {
          clearInterval(fadeOutInterval);
          return 0;
        }
        return prev - 0.5;
      });
    }, 100);
  }, 400);
}

export function parseTable(text, customIsTableRow, customParseTableRow, customIsSeparatorRow) {
  if (!text.includes('|')) return null;
  
  const lines = text.split('\n');
  if (lines.length < 2) return null;
  
  // Use provided functions or fall back to the exported ones
  const tableRowFilter = customIsTableRow || isTableRow;
  const tableRowParser = customParseTableRow || parseTableRow;
  const separatorRowChecker = customIsSeparatorRow || isSeparatorRow;
  
  const tableRows = lines
    .filter(tableRowFilter)
    .map(tableRowParser)
    .filter(row => row.length > 1);
  
  if (tableRows.length < 2) return null;
  
  const headers = tableRows[0];
  const dataRows = separatorRowChecker(tableRows[1]) ? tableRows.slice(2) : tableRows.slice(1);
  
  return { headers, dataRows };
}

export function findAllTables(text, customIsTableRow, customParseTableRow, customIsSeparatorRow) {
  const lines = text.split('\n');
  const tables = [];
  let tableStart = -1;
  
  const tableRowFilter = customIsTableRow || isTableRow;
  const tableRowParser = customParseTableRow || parseTableRow;
  const separatorRowChecker = customIsSeparatorRow || isSeparatorRow;
  
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes('|')) {
      if (tableStart === -1) tableStart = i;
    } else if (tableStart !== -1 && !lines[i].trim()) {
      if (i - tableStart >= 2) {
        const tableText = lines.slice(tableStart, i).join('\n');
        const tableData = parseTable(tableText, tableRowFilter, tableRowParser, separatorRowChecker);
        
        if (tableData) {
          tables.push({
            startIndex: lines.slice(0, tableStart).join('\n').length,
            endIndex: lines.slice(0, i).join('\n').length,
            tableData
          });
        }
      }
      tableStart = -1;
    }
  }
  
  if (tableStart !== -1) {
    const tableText = lines.slice(tableStart).join('\n');
    const tableData = parseTable(tableText, tableRowFilter, tableRowParser, separatorRowChecker);
    
    if (tableData) {
      tables.push({
        startIndex: lines.slice(0, tableStart).join('\n').length,
        endIndex: text.length,
        tableData
      });
    }
  }
  
  return tables;
}

export const MarkdownText = ({ content }) => (
  <ReactMarkdown
    components={{
      h1: ({node, ...props}) => <h1 className="text-xl font-bold border-b border-[#40444B] pb-1 mb-3" {...props} />,
      h2: ({node, ...props}) => <h2 className="text-lg font-bold mt-4 mb-2" {...props} />,
      h3: ({node, ...props}) => <h3 className="text-base font-bold mt-3 mb-1" {...props} />,
      p: ({node, ...props}) => <p className="my-1" {...props} />,
      ul: ({node, ...props}) => <ul className="list-disc pl-5 my-2" {...props} />,
      li: ({node, ...props}) => <li className="my-0.5" {...props} />,
      pre: ({node, ...props}) => <pre className="bg-[#2F3136] rounded-lg p-4 my-2 overflow-x-auto" {...props} />,
      code: ({node, inline, className, children, ...props}) => {
        if (inline) {
          return <code className="bg-[#2F3136] rounded px-1 py-0.5 text-sm" {...props}>{children}</code>
        }
        return (
          <code className="block text-sm font-mono" {...props}>
            {children}
          </code>
        )
      }
    }}
  >
    {content}
  </ReactMarkdown>
);

export const TableView = ({ tableData }) => (
  <div className="my-4 overflow-x-auto rounded-lg">
    <table className="min-w-full bg-[#2F3136] rounded-lg border-collapse">
      <thead>
        <tr className="bg-[#202225] border-b border-[#40444B]">
          {tableData.headers.map((header, i) => (
            <th key={i} className="px-4 py-3 text-left text-sm font-semibold">
              {header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {tableData.dataRows.map((row, i) => (
          <tr key={i} className={i % 2 === 0 ? 'bg-[#36393F]' : 'bg-[#32353B]'}>
            {row.map((cell, j) => (
              <td key={j} className="px-4 py-2 text-sm border-t border-[#40444B]">
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

export const ContentRenderer = ({ content, hasCompleted, customIsTableRow, customParseTableRow, customIsSeparatorRow }) => {
  const tables = findAllTables(content, customIsTableRow, customParseTableRow, customIsSeparatorRow);
  
  const segments = [];
  let lastEnd = 0;
  
  tables.forEach(table => {
    if (table.startIndex > lastEnd) {
      segments.push({
        type: 'text',
        content: content.substring(lastEnd, table.startIndex)
      });
    }
    
    segments.push({
      type: 'table',
      tableData: table.tableData
    });
    
    lastEnd = table.endIndex;
  });
  
  if (lastEnd < content.length) {
    segments.push({
      type: 'text',
      content: content.substring(lastEnd)
    });
  }

  if (segments.length === 0) {
    segments.push({
      type: 'text',
      content: content
    });
  }

  return (
    <div 
      className="prose prose-invert prose-headings:mb-2 prose-headings:mt-4 prose-p:my-1 first:prose-headings:mt-0"
      style={{
        opacity: hasCompleted ? 1 : 0.5,
        transition: "opacity 0.5s ease-in-out"
      }}
    >
      {segments.map((segment, index) => (
        <div key={index}>
          {segment.type === 'text' 
            ? <MarkdownText content={segment.content} />
            : <TableView tableData={segment.tableData} />
          }
        </div>
      ))}
    </div>
  );
};

export const isTableRow = line => line.includes('|') && line.trim();
export const parseTableRow = line => line.split('|').map(cell => cell.trim()).filter(cell => cell !== '');
export const isSeparatorRow = row => row.every(cell => cell.includes('-'));
