import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { useAuth, AuthProvider } from './contexts/AuthContext';
import Sidebar from './components/Sidebar';

// Lazy-load pages for fast initial load
const LoginPage     = lazy(() => import('./pages/LoginPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const CaseDetailPage= lazy(() => import('./pages/CaseDetailPage'));
const MetricsPage   = lazy(() => import('./pages/MetricsPage'));
const HelpPage      = lazy(() => import('./pages/HelpPage'));
const AuditPage     = lazy(() => import('./pages/AuditPage'));

function PageLoader() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <span className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full spin-slow" />
    </div>
  );
}

/** Redirect to login if not authenticated */
function PrivateRoute() {
  const { token } = useAuth();
  return token ? <Outlet /> : <Navigate to="/login" replace />;
}

/** Redirect to dashboard if already logged in */
function PublicRoute() {
  const { token } = useAuth();
  return token ? <Navigate to="/dashboard" replace /> : <Outlet />;
}

/** Admin-only route */
function AdminRoute() {
  const { isAdmin } = useAuth();
  return isAdmin ? <Outlet /> : <Navigate to="/dashboard" replace />;
}

/** Shared layout with sidebar */
function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto flex flex-col">
        <Suspense fallback={<PageLoader />}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Public */}
            <Route element={<PublicRoute />}>
              <Route path="/login" element={<LoginPage />} />
            </Route>

            {/* Protected with layout */}
            <Route element={<PrivateRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/case/:id"  element={<CaseDetailPage />} />
                <Route path="/metrics"   element={<MetricsPage />} />
                <Route path="/help"      element={<HelpPage />} />

                {/* Admin only */}
                <Route element={<AdminRoute />}>
                  <Route path="/audit" element={<AuditPage />} />
                </Route>
              </Route>
            </Route>

            {/* Default */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}
