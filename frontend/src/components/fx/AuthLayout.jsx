import { Component, lazy, Suspense } from 'react';

const SignalScene = lazy(() => import('./SignalScene.jsx'));

// The WebGL scene is decorative. A rendering or chunk-loading failure must never
// prevent users from reaching the authentication form.
class SceneErrorBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? null : this.props.children;
  }
}

export default function AuthLayout({ children }) {
  return (
    <div
      className="relative min-h-screen overflow-hidden bg-neutral"
      style={{ backgroundImage: 'radial-gradient(ellipse at 50% 35%, #2B3240 0%, #1B2029 70%)' }}
    >
      <div className="absolute inset-0" aria-hidden="true">
        <SceneErrorBoundary>
          <Suspense fallback={null}>
            <SignalScene />
          </Suspense>
        </SceneErrorBoundary>
      </div>
      <div className="relative z-10 flex min-h-screen items-center justify-center p-4">
        {children}
      </div>
    </div>
  );
}
