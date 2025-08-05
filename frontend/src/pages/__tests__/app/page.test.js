import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Chat from './page';

// Mock external dependencies
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
  },
}));

jest.mock('react-markdown', () => ({
  __esModule: true,
  default: ({ children }) => <div data-testid="markdown">{children}</div>,
}));

jest.mock('@/Components/ChatBots/ProgressTracker', () => ({
  ProgressTracker: ({ isVisible, progressIndicator }) => (
    <div data-testid="progress-tracker">
      {isVisible && <div>{progressIndicator}</div>}
    </div>
  ),
}));

jest.mock('@/Components/Universals/Menu', () => ({
  __esModule: true,
  default: ({ onCollapse, onReset }) => (
    <div data-testid="menu">
      <button onClick={() => onCollapse(true)}>Collapse</button>
      <button onClick={() => onReset()}>Reset</button>
    </div>
  ),
}));

// Mock fetch API
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock EventSource
class MockEventSource {
  constructor(url) {
    this.url = url;
    this.onmessage = null;
    this.onerror = null;
  }
  
  close() {}
}
global.EventSource = MockEventSource;

describe('Chat Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock successful server types fetch
    mockFetch.mockImplementationOnce(() => 
      Promise.resolve({
        json: () => Promise.resolve({ server_types: ['rfx', 'samsara', 'raw_rfx'] })
      })
    );
    // Mock successful init
    mockFetch.mockImplementationOnce(() => 
      Promise.resolve({
        json: () => Promise.resolve({
          status: 'connected',
          response: JSON.stringify({
            session_id: 'test-session',
            server_type: 'rfx'
          })
        })
      })
    );
  });

  test('renders initial state correctly', async () => {
    render(<Chat />);
    
    // Check for main UI elements
    expect(screen.getByTestId('menu')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Connecting to server/i)).toBeInTheDocument();
    
    // Wait for connection
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Analyze RFX data/i)).toBeInTheDocument();
    });
  });

  test('handles user input correctly', async () => {
    render(<Chat />);
    
    // Wait for connection
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Analyze RFX data/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/Analyze RFX data/i);
    await userEvent.type(input, 'Test message');
    
    expect(input).toHaveValue('Test message');
  });

  test('submits messages and handles responses', async () => {
    render(<Chat />);
    
    // Wait for connection
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Analyze RFX data/i)).toBeInTheDocument();
    });

    // Mock successful query response
    mockFetch.mockImplementationOnce(() => 
      Promise.resolve({
        json: () => Promise.resolve({
          status: 'success',
          response: 'Test response'
        })
      })
    );

    const input = screen.getByPlaceholderText(/Analyze RFX data/i);
    await userEvent.type(input, 'Test message{enter}');

    // Check if message appears in chat
    await waitFor(() => {
      expect(screen.getByText('Test message')).toBeInTheDocument();
    });

    // Check if response appears
    await waitFor(() => {
      expect(screen.getByText('Test response')).toBeInTheDocument();
    });
  });

  test('handles server type changes', async () => {
    const { rerender } = render(<Chat />);
    
    // Wait for initial connection
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Analyze RFX data/i)).toBeInTheDocument();
    });

    // Mock successful server change
    mockFetch
      .mockImplementationOnce(() => 
        Promise.resolve({
          json: () => Promise.resolve({
            status: 'connected',
            response: JSON.stringify({
              session_id: 'new-session',
              server_type: 'samsara'
            })
          })
        })
      );

    // Simulate server type change
    await act(async () => {
      await screen.getByTestId('agentic-accordion').props.handleServerTypeChange('samsara');
    });

    // Check if placeholder text changed
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Ask about Samsara documents/i)).toBeInTheDocument();
    });
  });

  test('handles suggestions correctly', async () => {
    render(<Chat />);
    
    // Wait for connection
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Analyze RFX data/i)).toBeInTheDocument();
    });

    // Find suggestion buttons
    const suggestions = screen.getAllByRole('button').filter(button => 
      button.textContent && !['Collapse', 'Reset'].includes(button.textContent)
    );

    // Click first suggestion
    await userEvent.click(suggestions[0]);

    // Check if suggestion text appears in input
    const input = screen.getByPlaceholderText(/Analyze RFX data/i);
    expect(input).toHaveValue(suggestions[0].textContent);
  });

  test('handles errors gracefully', async () => {
    // Mock failed init
    mockFetch.mockReset();
    mockFetch
      .mockImplementationOnce(() => 
        Promise.resolve({
          json: () => Promise.resolve({ server_types: ['rfx', 'samsara', 'raw_rfx'] })
        })
      )
      .mockImplementationOnce(() => 
        Promise.resolve({
          json: () => Promise.resolve({
            status: 'error',
            message: 'Connection failed'
          })
        })
      );

    render(<Chat />);

    // Check for error message
    await waitFor(() => {
      expect(screen.getByText(/Error connecting to MCP server/i)).toBeInTheDocument();
    });
  });
});
