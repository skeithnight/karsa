'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ErrorState } from '../shared/ErrorState';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class WorkspaceErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Workspace error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-6">
          <ErrorState 
            errorMessage={`Workspace Error: ${this.state.error?.message}`}
            onRetry={() => this.setState({ hasError: false, error: null })} 
          />
        </div>
      );
    }
    return this.props.children;
  }
}
