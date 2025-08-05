# Project Structure Documentation

## Overview

This project demonstrates a sophisticated **agentic AI platform** with a clean, professional architecture designed for portfolio presentation. The structure follows modern development practices and clearly separates concerns between frontend, backend, and specialized AI agents.

## Directory Structure

```
agentic-ai-knowledge-base/
├── 📁 frontend/                    # Next.js React Application
│   ├── 📁 src/
│   │   ├── 📁 components/          # Reusable UI Components
│   │   │   ├── 📁 ChatBots/        # Chat interface components
│   │   │   └── 📁 Universals/      # Shared UI components
│   │   ├── 📁 pages/               # Next.js pages and layouts
│   │   ├── 📁 utils/               # Utility functions
│   │   ├── 📁 hooks/               # Custom React hooks
│   │   ├── 📁 styles/              # CSS and styling
│   │   └── 📁 types/               # TypeScript type definitions
│   ├── 📁 public/                  # Static assets
│   ├── 📁 tests/                   # Frontend test files
│   └── package.json                # Frontend dependencies
│
├── 📁 backend/                     # Python FastAPI Backend
│   ├── 📁 api/
│   │   └── 📁 gateway/             # Main API gateway
│   ├── 📁 agents/                  # Specialized AI Agents
│   │   ├── 📁 rfx_analyzer/        # RFX data analysis agent
│   │   ├── 📁 document_processor/  # Document processing agent
│   │   ├── 📁 samsara_integration/ # External API integration
│   │   └── 📁 raw_data_processor/  # Raw data processing agent
│   ├── 📁 core/                    # Core backend functionality
│   │   ├── 📁 mcp_client/          # MCP protocol client
│   │   ├── 📁 llm_integration/     # LLM integration layer
│   │   └── 📁 session_management/  # Session handling
│   ├── 📁 config/                  # Configuration files
│   ├── 📁 utils/                   # Backend utilities
│   ├── 📁 tests/                   # Backend test files
│   └── package.json                # Backend dependencies
│
├── 📁 docs/                        # Project documentation
├── README.md                       # Main project README
└── package.json                    # Root package.json (monorepo)
```

## Key Architectural Decisions

### 🏗️ **Monorepo Structure**
- **Root Level**: Manages the entire project with workspace configuration
- **Frontend/Backend Separation**: Clear boundaries between client and server code
- **Shared Configuration**: Common scripts and dependencies at the root level

### 🎯 **Frontend Organization**
- **Component-Based Architecture**: Reusable components organized by functionality
- **Page-Based Routing**: Next.js pages for different application views
- **Utility Separation**: Helper functions, hooks, and types in dedicated folders
- **Testing Structure**: Comprehensive test coverage for all components

### 🔧 **Backend Organization**
- **API Gateway Pattern**: Centralized API entry point with routing
- **Agent-Based Architecture**: Specialized AI agents for different data domains
- **Core Services**: Shared functionality for MCP, LLM integration, and sessions
- **Modular Design**: Each agent is self-contained with its own configuration

### 🤖 **AI Agent Structure**
Each agent follows a consistent pattern:
```
agent_name/
├── server.py              # Main agent implementation
├── requirements.txt       # Agent-specific dependencies
├── config.py             # Configuration settings
├── utils.py              # Agent utilities
└── tests/                # Agent-specific tests
```

## Development Workflow

### 🚀 **Getting Started**
```bash
# Install all dependencies
npm run install:all

# Start development servers
npm run dev

# Run tests
npm run test

# Build for production
npm run build
```

### 🔄 **Development Commands**
- `npm run dev`: Start both frontend and backend in development mode
- `npm run dev:frontend`: Start only the frontend
- `npm run dev:backend`: Start only the backend
- `npm run test`: Run all tests
- `npm run lint`: Run linting on frontend code

### 🏭 **Production Deployment**
- Frontend builds to static files for deployment
- Backend can be containerized with Docker
- Each agent can be deployed independently

## Portfolio Benefits

### 📋 **Clear Separation of Concerns**
- Frontend and backend are clearly separated
- Each AI agent has a specific responsibility
- Easy to understand and navigate

### 🎨 **Professional Structure**
- Follows industry best practices
- Scalable architecture for future growth
- Easy to maintain and extend

### 🔍 **Demonstrated Skills**
- **Full-Stack Development**: Next.js + FastAPI
- **AI/ML Systems**: Multi-agent orchestration
- **Modern Architecture**: Microservices and API design
- **Testing**: Comprehensive test coverage
- **DevOps**: Build and deployment scripts

### 📚 **Documentation**
- Clear project structure documentation
- README files for each major component
- Code comments and inline documentation

## Technology Stack

### Frontend
- **Framework**: Next.js 15.2.1 with React 19
- **Styling**: Tailwind CSS, NextUI, Framer Motion
- **Testing**: Jest, React Testing Library
- **State Management**: React Hooks

### Backend
- **Framework**: FastAPI with async/await
- **Protocol**: Model Context Protocol (MCP)
- **LLM Integration**: Google Generative AI, Claude
- **Database**: SQLite with async operations
- **Testing**: Pytest with async support

### AI Agents
- **RFX Analyzer**: SQLite database analysis
- **Document Processor**: Google Drive integration
- **Samsara Integration**: External API processing
- **Raw Data Processor**: Advanced document processing

This structure demonstrates advanced software engineering principles while maintaining clarity for portfolio presentation. 