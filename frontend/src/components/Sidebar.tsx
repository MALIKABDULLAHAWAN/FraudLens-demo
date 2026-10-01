import { NavLink, useNavigate } from 'react-router-dom';
import {
  Shield, LayoutDashboard, BarChart2, FileText, HelpCircle, LogOut, Lock,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/metrics',   label: 'Model Metrics', icon: BarChart2 },
  { to: '/help',      label: 'How to Test', icon: HelpCircle },
];

const adminItems = [
  { to: '/audit', label: 'Audit Log', icon: FileText },
];

export default function Sidebar() {
  const { email, role, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="w-60 shrink-0 h-screen sticky top-0 flex flex-col border-r border-slate-800 bg-[rgb(11,15,25)]">
      {/* Brand */}
      <div className="p-5 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
            <Shield className="w-4 h-4 text-indigo-400" />
          </div>
          <span className="font-bold text-white tracking-tight">FraudLens</span>
        </div>
        <p className="text-[10px] text-slate-500 mt-1 ml-10">Explainable Fraud Review</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`
            }
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {label}
          </NavLink>
        ))}

        {isAdmin && (
          <>
            <div className="pt-4 pb-1 px-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600 flex items-center gap-1">
                <Lock className="w-3 h-3" /> Admin
              </p>
            </div>
            {adminItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-purple-600/20 text-purple-300 border border-purple-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`
                }
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                {label}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      {/* User info + logout */}
      <div className="p-3 border-t border-slate-800">
        <div className="flex items-center gap-2.5 px-2 py-2 mb-1">
          <div className="w-7 h-7 rounded-full bg-indigo-600/30 flex items-center justify-center text-xs font-semibold text-indigo-300">
            {(email?.[0] ?? 'A').toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="text-xs font-medium text-slate-300 truncate">{email}</p>
            <p className="text-[10px] text-slate-500 capitalize">{role}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all duration-150"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
