import { Routes, Route, Navigate, useLocation, useNavigate, BrowserRouter } from 'react-router-dom';
import type { ReactElement } from 'react';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import LibraryPage from '@/pages/LibraryPage';
import RenderStatusPage from '@/pages/RenderStatusPage';
import { AuthProvider, useAuth } from '@/state/auth';
import ProjectsPage from '@/pages/ProjectsPage';
import ProjectDetailPage from '@/pages/ProjectDetailPage';
import SharedViewPage from '@/pages/SharedViewPage';
import { OnboardingWelcome } from '@/components/OnboardingWelcome';
import { useEffect, useState } from 'react';
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
import { FLAGS } from '@/flags';
import MaintenancePage from '@/pages/MaintenancePage';
import LandingPage from '@/pages/LandingPage';
import PublicTemplatesPage from '@/pages/PublicTemplatesPage';
import NotFoundPage from '@/pages/NotFoundPage';

export type AppUser = { user_id: string; tenant_id: string; roles: string[] };

function RequireAuth({ children }: { children: ReactElement }) {
  const { user, tokens } = useAuth();
  const loading = !!tokens && !user;
  if (loading) return <div>Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
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
  const ONBOARDING_ENABLED = (import.meta.env.VITE_ONBOARDING_ENABLED ?? 'true') === 'true';
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/renders/:jobId" element={<RenderStatusPage />} />
      </Routes>
    </BrowserRouter>
  );
}
