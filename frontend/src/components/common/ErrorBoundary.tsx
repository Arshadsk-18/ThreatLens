import React, { Component, ErrorInfo, ReactNode } from "react";
import { ErrorState } from "@/components/cx/ErrorState";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    console.error("ThreatLens ErrorBoundary caught an unhandled exception:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      const requestId = (this.state.error as { request_id?: string })?.request_id;
      return (
        <div className="min-h-screen bg-canvas flex items-center justify-center p-6">
          <div className="max-w-xl w-full">
            <ErrorState
              title="System Anomaly Encountered"
              message={
                this.state.error?.message ||
                "An unexpected runtime error occurred within the analyst interface."
              }
              requestId={requestId}
              onRetry={this.handleReset}
            />
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
