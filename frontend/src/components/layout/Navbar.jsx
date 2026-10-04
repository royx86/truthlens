import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ShieldCheck, ChevronDown, Menu, X, Trash2, User, Sparkles, LogIn, LogOut, UserPlus, History as HistoryIcon } from 'lucide-react';
import { clearHistory } from '../../utils/history';
import { useAuth } from '../../context/AuthContext';

export function Navbar({ onClearHistoryNotification }) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [teamsModalOpen, setTeamsModalOpen] = useState(false);
  const dropdownRef = useRef(null);
  const location = useLocation();
  const navigate = useNavigate();

  const { user, isAuthenticated, logout } = useAuth();

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const handleClearHistory = () => {
    clearHistory();
    setDropdownOpen(false);
    if (onClearHistoryNotification) {
      onClearHistoryNotification();
    } else {
      if (location.pathname === '/history') {
        window.location.reload();
      }
    }
  };

  const handleLogout = async () => {
    setDropdownOpen(false);
    await logout();
    navigate('/');
  };

  const navLinks = [
    { label: 'How it works', href: '/how-it-works' },
    { label: 'History', href: '/history' },
    { label: 'For teams', action: () => setTeamsModalOpen(true) },
    { label: 'About', href: '/about' },
  ];

  const userInitial = user?.name ? user.name.charAt(0).toUpperCase() : 'U';

  return (
    <>
      {/* Top micro banner */}
      <div className="bg-gradient-to-r from-violet-950 via-violet-900 to-indigo-900 text-violet-200 text-xs py-1.5 px-4 text-center font-medium border-b border-violet-800">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
          <span className="text-white font-semibold">TruthLens</span> helps you verify what you see online with evidence-backed AI analysis.
        </span>
      </div>

      {/* Main Navbar */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-slate-200 shadow-sm shadow-violet-100/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Left: Brand */}
          <Link
            to="/"
            className="flex items-center gap-2.5 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-600 rounded-lg p-1"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-700 flex items-center justify-center text-white shadow-sm shadow-violet-500/30 group-hover:from-violet-700 group-hover:to-indigo-800 transition-all">
              <ShieldCheck className="w-5 h-5 stroke-[2.2]" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-lg text-slate-900 tracking-tight leading-tight">
                TruthLens
              </span>
              <span className="text-[9px] font-bold text-violet-600 tracking-widest uppercase leading-none">
                AI VERIFICATION
              </span>
            </div>
          </Link>

          {/* Center: Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-7" aria-label="Main Navigation">
            {navLinks.map((link) =>
              link.href ? (
                <Link
                  key={link.label}
                  to={link.href}
                  className={`text-sm font-medium transition-colors hover:text-violet-600 ${
                    location.pathname === link.href ? 'text-violet-600 font-semibold' : 'text-slate-600'
                  }`}
                >
                  {link.label}
                </Link>
              ) : (
                <button
                  key={link.label}
                  type="button"
                  onClick={link.action}
                  className="text-sm font-medium text-slate-600 hover:text-violet-600 transition-colors cursor-pointer"
                >
                  {link.label}
                </button>
              )
            )}
          </nav>

          {/* Right: Auth Buttons / Avatar Dropdown & Mobile Toggle */}
          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  type="button"
                  id="user-profile-menu-button"
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  aria-expanded={dropdownOpen}
                  aria-haspopup="true"
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-full border border-violet-200 hover:border-violet-300 hover:bg-violet-50/50 transition-all focus:outline-none focus:ring-2 focus:ring-violet-500 cursor-pointer"
                >
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-violet-600 to-indigo-700 text-white flex items-center justify-center text-xs font-bold">
                    {userInitial}
                  </div>
                  <span className="text-xs font-semibold text-slate-700 hidden sm:inline max-w-[120px] truncate">
                    {user?.name || 'Account'}
                  </span>
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400 stroke-[2.5]" />
                </button>

                {/* User Dropdown */}
                {dropdownOpen && (
                  <div
                    className="absolute right-0 mt-2 w-52 bg-white rounded-2xl shadow-xl shadow-violet-100/60 border border-violet-100 py-1.5 z-50 animate-in fade-in slide-in-from-top-2 duration-150"
                    role="menu"
                    aria-orientation="vertical"
                    aria-labelledby="user-profile-menu-button"
                  >
                    <div className="px-3.5 py-2.5 border-b border-slate-100">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-xl bg-violet-100 text-violet-700 flex items-center justify-center text-xs font-bold shrink-0">
                          {userInitial}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-bold text-slate-900 truncate">{user?.name || 'User'}</p>
                          <p className="text-[11px] text-slate-400 truncate">{user?.email}</p>
                        </div>
                      </div>
                    </div>
                    <div className="py-1">
                      <button
                        type="button"
                        onClick={() => {
                          navigate('/history');
                          setDropdownOpen(false);
                        }}
                        className="w-full text-left px-3.5 py-2 text-xs text-slate-700 hover:bg-violet-50 flex items-center gap-2 cursor-pointer transition-colors"
                        role="menuitem"
                      >
                        <HistoryIcon className="w-3.5 h-3.5 text-slate-400" />
                        <span>Analysis History</span>
                      </button>
                      <button
                        type="button"
                        onClick={handleClearHistory}
                        className="w-full text-left px-3.5 py-2 text-xs text-slate-600 hover:bg-slate-50 flex items-center gap-2 cursor-pointer transition-colors"
                        role="menuitem"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-slate-400" />
                        <span>Clear Local History</span>
                      </button>
                    </div>
                    <div className="pt-1 border-t border-slate-100">
                      <button
                        type="button"
                        onClick={handleLogout}
                        className="w-full text-left px-3.5 py-2 text-xs text-rose-600 hover:bg-rose-50 flex items-center gap-2 cursor-pointer transition-colors font-medium"
                        role="menuitem"
                      >
                        <LogOut className="w-3.5 h-3.5 text-rose-500" />
                        <span>Log out</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="px-3 py-1.5 text-xs font-semibold text-slate-700 hover:text-violet-700 hover:bg-violet-50 rounded-lg transition-colors inline-flex items-center gap-1.5"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  <span>Log in</span>
                </Link>
                <Link
                  to="/signup"
                  className="px-3.5 py-1.5 text-xs font-semibold text-white bg-gradient-to-r from-violet-600 to-indigo-700 hover:from-violet-700 hover:to-indigo-800 rounded-xl shadow-sm shadow-violet-500/25 transition-all inline-flex items-center gap-1.5"
                >
                  <UserPlus className="w-3.5 h-3.5" />
                  <span>Sign up</span>
                </Link>
              </div>
            )}

            {/* Mobile hamburger menu button */}
            <button
              type="button"
              id="mobile-menu-toggle"
              aria-label="Toggle navigation menu"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-slate-600 hover:text-violet-700 hover:bg-violet-50 focus:outline-none focus:ring-2 focus:ring-violet-500"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-violet-100 bg-white px-4 pt-2 pb-4 space-y-2 shadow-md">
            {isAuthenticated && (
              <div className="px-3 py-2 bg-violet-50/70 rounded-xl mb-2 flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-violet-600 text-white flex items-center justify-center text-xs font-bold">
                  {userInitial}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-bold text-slate-900 truncate">{user?.name}</div>
                  <div className="text-[11px] text-slate-500 truncate">{user?.email}</div>
                </div>
              </div>
            )}

            {navLinks.map((link) =>
              link.href ? (
                <Link
                  key={link.label}
                  to={link.href}
                  className={`block px-3 py-2 rounded-md text-sm font-medium ${
                    location.pathname === link.href
                      ? 'bg-violet-50 text-violet-700 font-semibold'
                      : 'text-slate-700 hover:bg-violet-50'
                  }`}
                >
                  {link.label}
                </Link>
              ) : (
                <button
                  key={link.label}
                  type="button"
                  onClick={() => {
                    link.action();
                    setMobileMenuOpen(false);
                  }}
                  className="w-full text-left block px-3 py-2 rounded-md text-sm font-medium text-slate-700 hover:bg-violet-50 cursor-pointer"
                >
                  {link.label}
                </button>
              )
            )}

            <div className="pt-2 border-t border-slate-100 space-y-1.5">
              {isAuthenticated ? (
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full text-left px-3 py-2 rounded-md text-sm font-medium text-rose-600 hover:bg-rose-50 flex items-center gap-2 cursor-pointer"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Log out</span>
                </button>
              ) : (
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <Link
                    to="/login"
                    className="text-center px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 border border-slate-200 hover:bg-violet-50"
                  >
                    Log in
                  </Link>
                  <Link
                    to="/signup"
                    className="text-center px-3 py-2 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-violet-600 to-indigo-700 shadow-sm"
                  >
                    Sign up
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </header>

      {/* For Teams Modal */}
      {teamsModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl shadow-violet-100/50 border border-violet-100 relative">
            <button
              type="button"
              onClick={() => setTeamsModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
              aria-label="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="w-12 h-12 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center mb-4">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">TruthLens for Newsrooms & Teams</h3>
            <p className="text-sm text-slate-600 mt-2 leading-relaxed">
              TruthLens Enterprise provides automated feed monitoring, multi-analyst claim review workflows, custom veracity thresholds, and direct API integrations for fact-checking organizations.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setTeamsModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-gradient-to-r from-violet-600 to-indigo-700 text-white hover:from-violet-700 hover:to-indigo-800 transition-all shadow-sm shadow-violet-500/20 cursor-pointer"
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
