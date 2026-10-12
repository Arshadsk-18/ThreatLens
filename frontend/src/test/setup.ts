import '@testing-library/jest-dom';
import { configure } from '@testing-library/dom';

configure({ asyncUtilTimeout: 4000 });

class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== 'undefined') {
  window.ResizeObserver = MockResizeObserver;
}
global.ResizeObserver = MockResizeObserver;
