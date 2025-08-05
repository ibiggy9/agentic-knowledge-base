import { scrollToBottom, handleTyping, ContentRenderer } from './ChatUtils';
import { render } from '@testing-library/react';

describe('ChatUtils', () => {
  describe('scrollToBottom', () => {
    test('scrolls element to bottom', () => {
      const mockRef = {
        current: {
          scrollIntoView: jest.fn()
        }
      };

      scrollToBottom(mockRef);
      expect(mockRef.current.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth' });
    });

    test('handles null ref', () => {
      const mockRef = { current: null };
      expect(() => scrollToBottom(mockRef)).not.toThrow();
    });
  });

  describe('ContentRenderer', () => {
    test('renders markdown content', () => {
      const content = '**Hello World**';
      const { container } = render(
        <ContentRenderer content={content} hasCompleted={true} />
      );
      expect(container).toHaveTextContent('Hello World');
    });

    test('handles incomplete content', () => {
      const content = 'Loading...';
      const { container } = render(
        <ContentRenderer content={content} hasCompleted={false} />
      );
      expect(container).toHaveTextContent('Loading...');
    });
  });
});
