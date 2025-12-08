import { Link, Outlet, useLocation } from 'react-router-dom';

export default function AdminDashboard() {
  const { pathname } = useLocation();
  return (
    <div className="p-4">
      <h1 className="text-xl font-semibold mb-4">Admin Dashboard</h1>
      <div className="flex gap-4 mb-4">
        <Link to="/admin/users" className={`text-sm ${pathname.includes('/admin/users') ? 'text-indigo-600' : 'text-gray-600'}`}>Users</Link>
        <Link to="/admin/jobs" className={`text-sm ${pathname.includes('/admin/jobs') ? 'text-indigo-600' : 'text-gray-600'}`}>Jobs</Link>
        <Link to="/admin/usage" className={`text-sm ${pathname.includes('/admin/usage') ? 'text-indigo-600' : 'text-gray-600'}`}>Usage</Link>
      </div>
      <Outlet />
    </div>
  );
}
