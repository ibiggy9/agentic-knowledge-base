'use client';
import { useState, useEffect, useRef, useCallback, memo } from 'react';
import { motion } from 'framer-motion';
import { IoSend } from 'react-icons/io5';
import { IoMdAdd } from 'react-icons/io';
import { IoMicOutline } from 'react-icons/io5';
import { ProgressTracker } from '@/Components/ChatBots/ProgressTracker';
import ReactMarkdown from 'react-markdown';
import Menu from '@/Components/Universals/Menu';
import AgenticAccordion from '@/Components/ChatBots/Agentic_Accordion';
import React from 'react';
import { scrollToBottom, ContentRenderer } from '@/Components/ChatBots/ChatUtils';

const MemoizedMenu = memo(Menu);
const MemoizedAgenticAccordion = memo(AgenticAccordion);

export default function Chat() {
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isMenuCollapsed, setIsMenuCollapsed] = useState(false);
  const [showAddTooltip, setShowAddTooltip] = useState(false);
  const [showMicTooltip, setShowMicTooltip] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [progressIndicator, setProgressIndicator] = useState('');
  const [progressDetails, setProgressDetails] = useState([]);
  const [isMobile, setIsMobile] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [serverType, setServerType] = useState('rfx');
  const [serverTypes, setServerTypes] = useState([]);
  const eventSourceRef = useRef(null);
  const messagesEndRef = useRef(null);
  const [isTyping, setIsTyping] = useState(false);
  const [glowIntensity, setGlowIntensity] = useState(0);
  const typingTimeoutRef = useRef(null);
  const textareaRef = useRef(null);
  const serverTypeRef = useRef(serverType);
  const sessionIdRef = useRef(sessionId);

  useEffect(() => {
    serverTypeRef.current = serverType;
    sessionIdRef.current = sessionId;
  }, [serverType, sessionId]);

  useEffect(() => {
    const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
    if (isSafari) {
      document.body.classList.add('safari');
    }

    return () => {
      document.body.classList.remove('safari');
    };
  }, []);

  useEffect(() => {
    fetchServerTypes();
    initSession(serverType);

    return () => {
      if (sessionId) {
        fetch(`${API_BASE}/api/session/${sessionId}`, {
          method: 'DELETE',
        }).catch(console.error);
      }

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [serverType]);

  useEffect(() => {
    if (isConnected) {
      setSuggestions(generateRandomSuggestions(serverType));
    }
  }, [isConnected, serverType]);

  const userInputsRfx = [
    'Give me an overview of the RFX data.',
    'What are the key trends in our RFPs?',
    'Tell me anything interesting about our data.',
    'What insights can you find in the RFX data?',
    'Show me a summary of the data.',
    'What are the main takeaways from the RFX information?',
    'Can you provide a general analysis of the data?',
    'Highlight any significant patterns in the data.',
    "What's the overall status of our RFPs?",
    'Give me a broad overview of the RFX performance.',

    'What is the win rate by region?',
    'Show me RFP volume by region.',
    'Which regions are performing best?',
    'Which regions are performing worst?',
    'Compare RFP activity across different regions.',
    'Analyze the data by geographical location.',
    'What are the regional trends in win/loss rates?',
    'Show me a breakdown of RFPs by country.',
    "What's the distribution of deals across regions?",

    'Which industries are most represented in our RFPs?',
    'What is the win rate by industry?',
    'Show me the distribution of RFPs across different sectors.',
    'Analyze the data by industry vertical.',
    'Which industries are most successful for us?',
    'Which industries are most challenging?',
    'Are there any industry-specific win/loss patterns?',
    'Compare our performance across different industries.',

    `What is the win rate trend over the past year (today is ${new Date().toLocaleDateString()}).`,
    `Analyze RFP volume by month up to ${new Date().toLocaleDateString()}.`,
    `How did sales perform in Q${Math.floor((new Date().getMonth() + 3) / 3) - 1 || 4} ${new Date().getFullYear() - (Math.floor((new Date().getMonth() + 3) / 3) === 1 ? 1 : 0)}?`,
    `Compare Q${Math.floor((new Date().getMonth() + 3) / 3)} ${new Date().getFullYear()}'s performance to Q${Math.floor((new Date().getMonth() + 3) / 3) - 1 || 4} ${new Date().getFullYear() - (Math.floor((new Date().getMonth() + 3) / 3) === 1 ? 1 : 0)}.`,
    'Show me the trend of win/loss ratios over time.',
    'Are there any seasonal patterns in the data?',
    'How has the number of RFPs changed over time?',
    `Analyze the data for year-over-year trends (${new Date().getFullYear() - 1} vs ${new Date().getFullYear()}).`,

    `What is the most common loss reason as of ${new Date().toLocaleDateString()}?`,
    `How many RFPs did we win in ${new Date(new Date().setMonth(new Date().getMonth() - 1)).toLocaleString('default', { month: 'long' })} ${new Date().getFullYear()}?`,
    'What is the total value of won deals?',
    'What percentage of RFPs are successful?',
    `How many deals are currently in the pipeline as of ${new Date().toLocaleDateString()}?`,
  ];

  const userInputsSamsara = [
    "What are Samsara's key competitive advantages in the market?",
    'How does Samsara position themselves in the market?',
    'What market segments is Samsara gaining traction in?',
    "Identify Samsara's growth strategy and market expansion plans",
    'What industry trends is Samsara capitalizing on?',

    'Give me a comprehensive overview of Samsara',
    "What are Samsara's key strengths and weaknesses?",
    'How does Samsara differentiate from other competitors?',
    "Generate an executive summary of Samsara's competitive position",
    'What threats does Samsara face in the current market?',

    "What is Samsara's current financial performance?",
    "How has Samsara's revenue growth trended over time?",
    "Compare Samsara's profitability metrics to industry standards",
    "What are Samsara's key financial advantages over competitors?",
    'How is Samsara allocating resources for growth?',

    "What are Samsara's flagship products?",
    "Where does Samsara's product offering excel in the market?",
    'What unique value propositions does Samsara offer customers?',
    'What innovations is Samsara focusing on in their product strategy?',
    "How does Samsara's technology stack compare to industry standards?",

    "What is Samsara's current go-to-market strategy?",
    'Which customer segments is Samsara most successful with?',
    "How does Samsara's pricing compare to industry standards?",
    "Analyze Samsara's marketing messaging and brand positioning",
    'Create a detailed SWOT analysis of Samsara',

    "What is Samsara's pricing strategy in competitive deals?",
    "How effective is Samsara's sales approach?",
    'What customer success stories is Samsara leveraging?',
    "Who are Samsara's strategic partners and how do they leverage them?",
    'Which geographical markets is Samsara prioritizing for expansion?',
  ];

  const userInputsRawRfx = [
    'What are the most requested features in recent RFPs?',
    'Which product capabilities are customers prioritizing in their requirements?',
    'What integration capabilities are most frequently requested in RFPs?',
    'Identify emerging feature trends across recent RFX submissions',
    'What technical specifications are most commonly required in fleet management RFPs?',

    'What are the top compliance requirements customers are asking for?',
    'How are security requirements evolving in recent RFX documents?',
    'What reporting capabilities do customers expect in their telematics solutions?',
    'What data management features are customers requesting most often?',
    'What mobile app capabilities are customers demanding in RFPs?',

    'What are the unique requirements for government fleet management RFPs?',
    'How do feature requirements differ between transportation and construction industries?',
    'What specialized features are requested for EV fleet management?',
    'What are the most common requirements for heavy equipment tracking?',
    'What safety features are most requested in commercial fleet RFPs?',

    'What implementation timelines are customers expecting in RFPs?',
    'What training and support requirements appear most frequently?',
    'What customization capabilities are customers looking for?',
    'What API and developer tools are customers requesting?',
    'What SLA requirements are most common in enterprise RFPs?',

    'What product gaps exist based on customer RFP requirements?',
    'Which feature requests align with our current product roadmap?',
    'What competitive differentiators should we highlight based on RFP trends?',
    'What emerging customer needs should inform our product strategy?',
    'What are the most common deal-breaker requirements in lost RFPs?',
  ];

  const generateRandomSuggestions = (currentServerType) => {
    const inputList =
      currentServerType === 'rfx'
        ? userInputsRfx
        : currentServerType === 'raw_rfx'
          ? userInputsRawRfx
          : userInputsSamsara;
    const shuffled = [...inputList].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, 4);
  };

  async function initSession(serverType) {
    setIsConnecting(true);
    setProgressIndicator(
      serverType === 'rfx'
        ? 'Connecting to RFX knowledge base...'
        : 'Connecting to Samsara knowledge base...',
    );

    try {
      const response = await fetch(`${API_BASE}/api/init`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          server_type: serverType,
        }),
      });

      const data = await response.json();
      if (data.status === 'connected') {
        const sessionInfo = JSON.parse(data.response);
        setSessionId(sessionInfo.session_id);
        setServerType(sessionInfo.server_type);
        setIsConnected(true);
        setMessages([
          {
            role: 'assistant',
            content: getWelcomeMessage(serverType),
          },
        ]);
      } else {
        setIsConnected(false);
        setMessages([
          {
            role: 'assistant',
            content: `Error connecting to MCP server: ${data.message}`,
          },
        ]);
      }
    } catch (error) {
      setIsConnected(false);
      setMessages([
        {
          role: 'assistant',
          content: `Error connecting to API: ${error.message}`,
        },
      ]);
    } finally {
      setIsConnecting(false);
      setProgressIndicator('');
    }
  }

  function getWelcomeMessage(serverType) {
    if (serverType === 'samsara') {
      return 'Connected to Samsara Analysis Server - How can I help you analyze Samsara documents?';
    } else if (serverType === 'raw_rfx') {
      return 'Connected to Raw RFX Server - I can help you analyze the most recent product demands from our customers.';
    } else {
      return 'Connected to RFX Database Server - How can I help you analyze RFX data?';
    }
  }

  async function fetchServerTypes() {
    try {
      const response = await fetch(`${API_BASE}/api/server-types`);
      const data = await response.json();
      if (data.server_types) {
        setServerTypes(data.server_types);
      }
    } catch (error) {
      console.error('Error fetching server types:', error);
    }
  }

  const handleMenuCollapse = useCallback((collapsed) => {
    setIsMenuCollapsed(collapsed);
  }, []);

  const handleResetChat = useCallback(async (newServerType = null) => {
    setIsConnecting(true);
    setProgressIndicator('Resetting chat...');

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    if (sessionIdRef.current) {
      try {
        await fetch(`${API_BASE}/api/session/${sessionIdRef.current}`, {
          method: 'DELETE',
        });
      } catch (error) {
        console.error('Error deleting session:', error);
      }
    }

    setMessages([]);
    setInputValue('');
    setProgressDetails([]);

    const typeToUse = newServerType || serverTypeRef.current;

    try {
      const requestBody = JSON.stringify({ server_type: typeToUse });

      const response = await fetch(`${API_BASE}/api/init`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: requestBody,
      });

      const data = await response.json();

      if (data.status === 'connected') {
        const sessionInfo = JSON.parse(data.response);
        setSessionId(sessionInfo.session_id);
        setServerType(sessionInfo.server_type);
        setIsConnected(true);
        setMessages([
          {
            role: 'assistant',
            content: getWelcomeMessage(typeToUse),
          },
        ]);
        setSuggestions(generateRandomSuggestions(typeToUse));
      } else {
        setIsConnected(false);
        setMessages([
          {
            role: 'assistant',
            content: `Error connecting to server: ${data.message || 'Unknown error occurred'}`,
          },
        ]);
        setSuggestions(generateRandomSuggestions(typeToUse));
      }
    } catch (error) {
      console.error('Error resetting chat:', error);
      setIsConnected(false);
      setMessages([
        {
          role: 'assistant',
          content: `Error connecting to API: ${error.message}`,
        },
      ]);
    } finally {
      setIsConnecting(false);
      setProgressIndicator('');
    }
  }, []);

  const handleServerTypeChange = useCallback(
    async (type) => {
      if (serverType === type) return;

      setIsConnecting(true);
      setProgressIndicator(
        type === 'rfx'
          ? 'Connecting to RFX knowledge base...'
          : 'Connecting to Samsara knowledge base...',
      );

      if (sessionId) {
        try {
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
          }

          await fetch(`${API_BASE}/api/session/${sessionId}`, {
            method: 'DELETE',
          });
        } catch (error) {
          console.error('Error deleting session:', error);
        }
      }

      setServerType(type);

      setMessages([]);
      setInputValue('');
      setProgressDetails([]);

      await initSession(type);

      setSuggestions(generateRandomSuggestions(type));

      setIsConnecting(false);
    },
    [serverType, sessionId],
  );

  const handleSuggestionClick = useCallback((suggestion) => {
    setInputValue(suggestion);
  }, []);

  function handleSubmit(e) {
    e.preventDefault();
    if (!inputValue.trim() || !isConnected || isLoading) return;

    const userMessage = inputValue;
    setMessages([...messages, { role: 'user', content: userMessage }]);
    setInputValue('');
    setIsLoading(true);
    setProgressDetails([]);

    if (textareaRef.current) {
      textareaRef.current.style.height = '60px';
    }

    setTimeout(handleScrollToBottom, 100);
    setSuggestions(generateRandomSuggestions(serverType));
    setProgressIndicator(serverType === 'rfx' ? 'Thinking...' : 'Processing documents...');

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const encodedQuery = encodeURIComponent(userMessage);
      const url = `${API_BASE}/api/query-stream?session_id=${sessionId}&query=${encodedQuery}`;

      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.details && data.details.status === 'completed') {
          // step completion
        }

        setProgressDetails((prev) => {
          const updatedDetails = [...prev];
          if (!updatedDetails.some((d) => JSON.stringify(d) === JSON.stringify(data))) {
            updatedDetails.push(data);
          }
          return updatedDetails;
        });

        setProgressIndicator(data.message || 'Processing...');

        if (data.type === 'final') {
          setIsTyping(true);
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: data.response,
              hasCompleted: false,
            },
          ]);

          setTimeout(() => {
            setMessages((prev) =>
              prev.map((msg, i) => (i === prev.length - 1 ? { ...msg, hasCompleted: true } : msg)),
            );
            setIsTyping(false);
          }, 100);

          setIsLoading(false);
          setProgressIndicator('');
          setSuggestions(generateRandomSuggestions(serverType));
          eventSource.close();
          eventSourceRef.current = null;
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE Error:', error);
        fallbackToRegularApi(userMessage);
        eventSource.close();
        eventSourceRef.current = null;
      };
    } catch (error) {
      console.error('Error setting up SSE:', error);
      fallbackToRegularApi(userMessage);
    }
  }

  async function fallbackToRegularApi(userMessage) {
    let progressPhases =
      serverType === 'rfx'
        ? [
            'Analyzing data...',
            'Running queries...',
            'Analyzing patterns...',
            'Generating insights...',
          ]
        : [
            'Processing documents...',
            'Extracting information...',
            'Analyzing content...',
            'Generating insights...',
          ];
    let currentPhaseIndex = 0;

    const progressInterval = setInterval(() => {
      setProgressIndicator(progressPhases[currentPhaseIndex]);
      currentPhaseIndex = (currentPhaseIndex + 1) % progressPhases.length;
    }, 2000);

    try {
      const response = await fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          query: userMessage,
        }),
      });

      clearInterval(progressInterval);

      const data = await response.json();

      if (data.status === 'success') {
        setMessages((prev) => [...prev, { role: 'assistant', content: data.response }]);
        setSuggestions(generateRandomSuggestions(serverType));
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: `Error: ${data.message || 'Unknown error occurred'}`,
          },
        ]);
        setSuggestions(generateRandomSuggestions(serverType));
      }
    } catch (error) {
      clearInterval(progressInterval);

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${error.message}`,
        },
      ]);
    } finally {
      setIsLoading(false);
      setProgressIndicator('');
    }
  }

  function handleScrollToBottom() {
    scrollToBottom(messagesEndRef);
  }

  const handleUserTyping = useCallback(
    debounce(() => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }

      setGlowIntensity(20);

      typingTimeoutRef.current = setTimeout(() => {
        const fadeOutInterval = setInterval(() => {
          setGlowIntensity((prev) => {
            if (prev <= 0.5) {
              clearInterval(fadeOutInterval);
              return 0;
            }
            return prev - 0.5;
          });
        }, 400);
      }, 400);
    }, 50),
    [],
  );

  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  return (
    <div className="flex min-h-screen bg-pink-700" style={{ backgroundColor: '#0e0e0f' }}>
      <div className="fixed">
        <MemoizedMenu onCollapse={handleMenuCollapse} onReset={handleResetChat} />
      </div>

      <div
        className="fixed top-0 right-0 h-24 z-10"
        style={{
          left: isMenuCollapsed ? '75px' : '300px',

          transition: 'left 0.3s ease',
        }}
      />

      <MemoizedAgenticAccordion
        isMenuCollapsed={isMenuCollapsed}
        serverType={serverType}
        handleServerTypeChange={handleServerTypeChange}
        isConnecting={isConnecting}
        isLoading={isLoading}
      />

      <motion.div
        initial={{ marginLeft: '75px' }}
        animate={{ marginLeft: isMenuCollapsed ? '75px' : '300px' }}
        transition={{ duration: 0.3, ease: 'linear' }}
        key="chat-container"
        className="flex-1 min-h-screen w-full"
        style={{
          backgroundColor: '#23272A',
        }}
      >
        <div className="flex flex-col h-screen max-w-4xl mx-auto p-4">
          <div
            className={`flex-1 mx-10 overflow-y-auto ${!isMobile ? 'pt-24' : 'pt-4'}`}
            style={{
              height: 'calc(100vh - 140px)',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {messages.length > 0 && messages[0].role === 'assistant' && messages.length === 1 && (
              <div key="welcome-message" className="flex justify-start mt-0">
                <motion.div
                  initial={{ opacity: 0, translateY: 50 }}
                  animate={{ opacity: 1, translateY: 0 }}
                  transition={{ duration: 2, type: 'spring', stiffness: 100, damping: 15 }}
                  className="max-w-[80%] rounded-2xl px-4 py-3 shadow-xl border border-[#42464D]"
                  style={{ backgroundColor: '#36393F', color: 'white' }}
                >
                  <div className="prose prose-invert prose-headings:mb-2 prose-headings:mt-4 prose-p:my-1 first:prose-headings:mt-0">
                    <ReactMarkdown>{messages[0].content}</ReactMarkdown>
                  </div>
                </motion.div>
              </div>
            )}

            {messages.map((message, index) => {
              if (index === 0 && messages.length === 1 && message.role === 'assistant') {
                return null;
              }

              return (
                <div
                  key={index}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <motion.div
                    initial={{ opacity: 0, translateY: 100 }}
                    animate={{ opacity: 1, translateY: 0 }}
                    transition={{ duration: 3.5, type: 'spring', stiffness: 100, damping: 15 }}
                    className={`max-w-[80%] rounded-2xl px-4 mt-2 py-3 mr-1 shadow-lg border ${
                      message.role === 'user' ? 'border-indigo-700' : 'border-[#42464D]'
                    }`}
                    style={{
                      backgroundColor: message.role === 'user' ? '#4338ca' : '#36393F',
                      backgroundImage:
                        message.role === 'user'
                          ? 'linear-gradient(to right, #4338ca, #5b21b6)'
                          : 'none',
                      color: 'white',
                    }}
                  >
                    {message.role === 'assistant' ? (
                      <ContentRenderer
                        content={message.content}
                        hasCompleted={message.hasCompleted}
                      />
                    ) : (
                      message.content
                    )}
                  </motion.div>
                </div>
              );
            })}

            {isLoading && (
              <div className="flex-grow mt-2">
                <ProgressTracker
                  isVisible={isLoading}
                  progressIndicator={progressIndicator}
                  progressDetails={progressDetails}
                  serverType={serverType}
                  onPlanLoaded={handleScrollToBottom}
                />
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <div className="mt-2 pb-1">
            {isConnected && !isLoading && suggestions.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3 px-4">
                {suggestions.map((suggestion, index) => (
                  <motion.button
                    initial={{ opacity: 0, scale: 0.6 }}
                    animate={{ opacity: 1, scale: 0.9 }}
                    transition={{
                      duration: 0.3,
                      delay: index * 0.1,
                      type: 'spring',
                      stiffness: 200,
                    }}
                    whileHover={{ scale: 1.05 }}
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="text-sm border rounded-2xl px-3 py-1.5 max-w-[200px] transition-colors shadow-md text-slate-200"
                    style={{
                      borderColor: index % 2 === 0 ? '#4338ca' : '#7c3aed',
                      backgroundColor: '#36393F',
                      backgroundImage:
                        index % 2 === 0
                          ? 'linear-gradient(to right, rgba(67, 56, 202, 0.7), #36393F)'
                          : 'linear-gradient(to right, rgba(124, 58, 237, 0.7), #36393F)',
                    }}
                  >
                    {suggestion}
                  </motion.button>
                ))}
              </div>
            )}

            <form onSubmit={handleSubmit} className="relative">
              <div className="relative">
                {glowIntensity > 0 && (
                  <div
                    className="absolute inset-0 rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-500 to-pink-500 transition-opacity duration-300"
                    style={{
                      opacity: glowIntensity / 20,
                      filter: `blur(${glowIntensity / 5}px)`,
                      backgroundSize: '200% 200%',
                      animation: 'moveGradient 3s ease infinite',
                    }}
                  ></div>
                )}

                <div className="relative bg-[#36393F] m-0.5 rounded-2xl text-white shadow-lg transition-all duration-300 flex items-center">
                  <div className="relative">
                    <button
                      type="button"
                      className="p-4 mb-1 ml-2 text-[#B9BBBE] hover:text-white transition-colors"
                      onMouseEnter={() => setShowAddTooltip(true)}
                      onMouseLeave={() => setShowAddTooltip(false)}
                      disabled={!isConnected}
                    >
                      <IoMdAdd size={24} />
                    </button>
                    {showAddTooltip && (
                      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-1 bg-[#18191C] text-white text-xs rounded whitespace-nowrap">
                        Coming Soon
                      </div>
                    )}
                  </div>

                  <div className="flex-1 relative overflow-hidden pr-24">
                    <textarea
                      ref={textareaRef}
                      value={inputValue}
                      onChange={(e) => {
                        setInputValue(e.target.value);
                        e.target.style.height = 'auto';
                        e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`;
                        handleUserTyping();
                      }}
                      onKeyDown={(e) => {
                        const newlines = (inputValue.match(/\n/g) || []).length;

                        if (e.key === 'Enter') {
                          if (e.shiftKey) {
                            return;
                          }

                          if (newlines === 0) {
                            e.preventDefault();
                            handleSubmit(e);
                          }
                        } else {
                          handleUserTyping();
                        }
                      }}
                      placeholder={
                        isConnected
                          ? serverType === 'rfx'
                            ? 'Analyze RFX data...'
                            : 'Ask about Samsara documents...'
                          : 'Connecting to server...'
                      }
                      className="w-full bg-transparent py-5 focus:outline-none placeholder-[#72767D] resize-none max-h-[180px] hide-scrollbar"
                      disabled={!isConnected}
                      rows={1}
                      style={{
                        minHeight: '60px',
                        maxHeight: '180px',
                        height: 'auto',
                        overflowY: 'auto',
                        scrollbarWidth: 'none',
                        msOverflowStyle: 'none',
                      }}
                    />
                  </div>

                  <div className="absolute right-4 flex items-center space-x-2">
                    <div className="relative">
                      <button
                        type="button"
                        className="p-2 mb-1 text-[#B9BBBE] hover:text-white transition-colors"
                        onMouseEnter={() => setShowMicTooltip(true)}
                        onMouseLeave={() => setShowMicTooltip(false)}
                        disabled={!isConnected}
                      >
                        <IoMicOutline size={20} />
                      </button>
                      {showMicTooltip && (
                        <div className="absolute bottom-full right-0 mb-2 px-3 py-1 bg-[#18191C] text-white text-xs rounded whitespace-nowrap">
                          Coming Soon
                        </div>
                      )}
                    </div>

                    {inputValue.trim() && (
                      <button
                        type="submit"
                        className={`p-2 ${isConnected && !isLoading ? 'text-[#5865F2] hover:text-[#7289DA]' : 'text-[#4F545C]'} transition-colors`}
                        disabled={!isConnected}
                      >
                        <IoSend size={20} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </form>
          </div>
        </div>
      </motion.div>
      <style jsx>{`
        @keyframes moveGradient {
          0% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 100% 50%;
          }
          100% {
            background-position: 0% 50%;
          }
        }

        .hide-scrollbar::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  );
}
