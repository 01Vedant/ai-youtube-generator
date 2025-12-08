import { useEffect, useState, type ReactElement } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import { LibraryPage } from '@/pages/LibraryPage';
import RenderStatusPage from '@/pages/RenderStatusPage';
import { AuthProvider, useAuth } from '@/state/auth';
import ProjectsPage from '@/pages/ProjectsPage';
import ProjectDetailPage from '@/pages/ProjectDetailPage';
import SharedViewPage from '@/pages/SharedViewPage';
import QueueAdminPage from '@/pages/QueueAdminPage';
import AdminDashboard from '@/pages/admin/AdminDashboard';
import AdminUsersPage from '@/pages/admin/AdminUsersPage';
import AdminJobsPage from '@/pages/admin/AdminJobsPage';
import AdminUsagePage from '@/pages/admin/AdminUsagePage';
import AdminAnalyticsPage from '@/pages/AdminAnalyticsPage';
import AdminFeatureFlagsPage from '@/pages/AdminFeatureFlagsPage';
import AdminLogsPage from '@/pages/AdminLogsPage';
import AdminWaitlistPage from '@/pages/AdminWaitlistPage';
import UsagePage from '@/pages/UsagePage';
import TemplatesPage from '@/pages/TemplatesPage';
import TemplateEditorPage from '@/pages/TemplateEditorPage';
import MarketplacePage from '@/pages/MarketplacePage';
import LegalIndexPage from '@/pages/LegalIndexPage';
import AdminFeedbackPage from './pages/AdminFeedbackPage';
import FeedbackButton from './components/FeedbackButton';
import MaintenancePage from '@/pages/MaintenancePage';
import LandingPage from '@/pages/LandingPage';
import PublicTemplatesPage from '@/pages/PublicTemplatesPage';
import NotFoundPage from '@/pages/NotFoundPage';

export type AppUser = { user_id: string; tenant_id: string; roles: string[] };

function RequireAuth({ children }: { children: ReactElement }) {
  const { user, tokens } = useAuth();
  const loading = !!tokens && !user;
  if (loading) return <div>Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppRoutes(): JSX.Element {
  const { user } = useAuth();
  const [onboardOpen, setOnboardOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  // Minimal shared handler: pages can call on maintenance error
  (window as any).__onApiError = (err: any) => {
    if (err?.maintenance === true && location.pathname !== '/maintenance') {
      navigate('/maintenance', { state: { maintenance: err.payload } });
    }
  };
  useEffect(() => {
    const seen = localStorage.getItem('bhaktigen.onboarded');
    setOnboardOpen(Boolean(user) && !seen);
  }, [user]);
  (window as any).__SHOW_ONBOARDING_MODAL = () => setOnboardOpen(true);

  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <DashboardPage />
            </RequireAuth>
          }
        />
        <Route
          path="/library"
          element={
            <RequireAuth>
              <LibraryPage />
            </RequireAuth>
          }
        />
        <Route
          path="/renders/:jobId"
          element={
            <RequireAuth>
              <RenderStatusPage />
            </RequireAuth>
          }
        />
        <Route
          path="/projects"
          element={
            <RequireAuth>
              <ProjectsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/projects/:id"
          element={
            <RequireAuth>
              <ProjectDetailPage />
            </RequireAuth>
          }
        />
        <Route path="/shared/:shareId" element={<SharedViewPage />} />
        <Route
          path="/queue"
          element={
            <RequireAuth>
              <QueueAdminPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin"
          element={
            <RequireAuth>
              <AdminDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/users"
          element={
            <RequireAuth>
              <AdminUsersPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/jobs"
          element={
            <RequireAuth>
              <AdminJobsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/usage"
          element={
            <RequireAuth>
              <AdminUsagePage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/analytics"
          element={
            <RequireAuth>
              <AdminAnalyticsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/flags"
          element={
            <RequireAuth>
              <AdminFeatureFlagsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/logs"
          element={
            <RequireAuth>
              <AdminLogsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/waitlist"
          element={
            <RequireAuth>
              <AdminWaitlistPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/feedback"
          element={
            <RequireAuth>
              <AdminFeedbackPage />
            </RequireAuth>
          }
        />
        <Route
          path="/usage"
          element={
            <RequireAuth>
              <UsagePage />
            </RequireAuth>
          }
        />
        <Route
          path="/templates"
          element={
            <RequireAuth>
              <TemplatesPage />
            </RequireAuth>
          }
        />
        <Route
          path="/templates/:id/edit"
          element={
            <RequireAuth>
              <TemplateEditorPage />
            </RequireAuth>
          }
        />
        <Route path="/marketplace" element={<MarketplacePage />} />
        <Route path="/legal" element={<LegalIndexPage />} />
        <Route path="/maintenance" element={<MaintenancePage />} />
        <Route path="/templates/public" element={<PublicTemplatesPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      {onboardOpen && <FeedbackButton />}
    </>
  );
}

export default function App(): JSX.Element {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
