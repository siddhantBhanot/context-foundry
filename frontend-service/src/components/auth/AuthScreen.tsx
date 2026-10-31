import React, { useState } from 'react';
import {
  AlertCircle,
  ArrowRight,
  Code2,
  Eye,
  EyeOff,
  Lock,
  Mail,
  ShieldCheck,
  Sparkles,
  User as UserIcon,
} from 'lucide-react';
import { useAuth } from '@/lib/auth/AuthContext';
import { ApiError } from '@/lib/api/client';
import { ContextFoundryLogo } from '@/components/brand/ContextFoundryLogo';

export function AuthScreen() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const role = 'developer';
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await signup(email, password, name, role);
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else if (err.message) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Authentication failed. Please check your credentials.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickLogin = async (demoEmail: string, demoRole: 'developer' | 'banking_staff') => {
    setErrorMessage(null);
    setIsSubmitting(true);
    setEmail(demoEmail);
    setPassword('password123');
    try {
      await login(demoEmail, 'password123');
    } catch (err: any) {
      // If demo account doesn't exist, sign it up
      try {
        const demoName = demoRole === 'banking_staff' ? 'Neha Kapoor (RM / Wealth)' : 'Hritik (Engineering)';
        await signup(demoEmail, 'password123', demoName, demoRole);
      } catch (signupErr: any) {
        setErrorMessage(signupErr?.message || 'Failed to sign in demo account.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#edf3f8] text-slate-800 flex flex-col justify-between p-4 sm:p-6 md:p-8 font-sans antialiased selection:bg-[#f05a28]/20 selection:text-[#f05a28]">
      {/* Top Brand Bar */}
      <div className="w-full max-w-5xl mx-auto flex items-center justify-between pt-2 sm:pt-4">
        <div className="flex items-center gap-2.5 text-left">
          <ContextFoundryLogo />
          <span className="text-[10px] font-bold text-slate-400 tracking-wider uppercase hidden sm:inline-block border-l border-slate-200 pl-2.5 self-center py-0.5">
            INTELLIGENCE PLATFORM
          </span>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-slate-200/80 text-[11px] font-medium text-slate-600 shadow-xs">
          <ShieldCheck className="w-3.5 h-3.5 text-[#f05a28]" />
          <span>ContextFoundry Enterprise</span>
        </div>
      </div>

      {/* Centered Auth Card */}
      <div className="w-full max-w-md mx-auto my-auto py-8">
        <div className="bg-white rounded-[28px] md:rounded-[36px] shadow-sm border border-slate-100 p-7 sm:p-9">
          {/* Card Header */}
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-orange-50 border border-orange-100 text-[#f05a28] mb-3 shadow-xs">
              <Sparkles className="w-6 h-6 text-[#f05a28]" />
            </div>
            <h2 className="text-2xl font-black tracking-tight text-slate-900">
              {mode === 'login' ? 'Sign In to ContextFoundry' : 'Create Your Account'}
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              {mode === 'login'
                ? 'Sign in to access Dev Central engineering intelligence and courses'
                : 'Join ContextFoundry to explore microservices and technical courses'}
            </p>
          </div>

          {/* Quick Demo Login */}
          {mode === 'login' && (
            <div className="mb-6 space-y-2">
              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block text-center">
                One-Click Demo Sign In
              </span>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => handleQuickLogin('engineer@contextfoundry.dev', 'developer')}
                className="w-full p-3.5 rounded-2xl border border-slate-200 hover:border-[#f05a28] bg-slate-50/70 hover:bg-orange-50/40 text-left transition-all cursor-pointer group disabled:opacity-50 flex items-center justify-between"
              >
                <div>
                  <div className="flex items-center gap-1.5 mb-1 text-slate-900 font-bold text-xs group-hover:text-[#f05a28]">
                    <Code2 className="w-4 h-4 text-[#f05a28]" />
                    <span>Software Engineer Demo</span>
                  </div>
                  <p className="text-[11px] text-slate-500 leading-tight">
                    Instant access to Dev Chat, Ingestion & Knowledge Cafe
                  </p>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-[#f05a28] transition-colors" />
              </button>

              <div className="relative flex py-2 items-center">
                <div className="grow border-t border-slate-200"></div>
                <span className="shrink mx-2 text-[10px] text-slate-400 font-bold uppercase">or email & password</span>
                <div className="grow border-t border-slate-200"></div>
              </div>
            </div>
          )}

          {/* Mode Switcher Tabs */}
          <div className="flex p-1 bg-slate-100 rounded-full border border-slate-200/80 mb-6">
            <button
              type="button"
              onClick={() => {
                setMode('login');
                setErrorMessage(null);
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-full transition-all cursor-pointer ${
                mode === 'login'
                  ? 'bg-[#f05a28] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('signup');
                setErrorMessage(null);
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-full transition-all cursor-pointer ${
                mode === 'signup'
                  ? 'bg-[#f05a28] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Error Message Banner */}
          {errorMessage && (
            <div
              role="alert"
              className="mb-5 p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5 animate-in fade-in slide-in-from-top-1 duration-200 shadow-xs"
            >
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1 font-medium leading-relaxed">{errorMessage}</div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'signup' && (
              <>
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                    Full Name
                  </label>
                  <div className="relative">
                    <UserIcon className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => {
                        setName(e.target.value);
                        if (errorMessage) setErrorMessage(null);
                      }}
                      placeholder="e.g. Siddhant Bhanot"
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:bg-white focus:outline-hidden focus:border-[#f05a28] focus:ring-2 focus:ring-[#f05a28]/20 transition-all"
                    />
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Corporate Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (errorMessage) setErrorMessage(null);
                  }}
                  placeholder="engineer@contextfoundry.dev"
                  className={`w-full bg-slate-50 border rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:bg-white focus:outline-hidden focus:ring-2 transition-all ${
                    errorMessage
                      ? 'border-rose-300 focus:border-rose-500 focus:ring-rose-500/20'
                      : 'border-slate-200 focus:border-[#f05a28] focus:ring-[#f05a28]/20'
                  }`}
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (errorMessage) setErrorMessage(null);
                  }}
                  placeholder="••••••••"
                  className={`w-full bg-slate-50 border rounded-xl pl-10 pr-10 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:bg-white focus:outline-hidden focus:ring-2 transition-all ${
                    errorMessage
                      ? 'border-rose-300 focus:border-rose-500 focus:ring-rose-500/20'
                      : 'border-slate-200 focus:border-[#f05a28] focus:ring-[#f05a28]/20'
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-3 bg-[#f05a28] hover:bg-[#d94b1c] active:scale-98 text-white font-semibold py-3 rounded-full transition-all shadow-xs flex items-center justify-center gap-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isSubmitting ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>{mode === 'login' ? 'Authenticate' : 'Create Account'}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Secure Platform Footer Note */}
          <div className="mt-6 pt-5 border-t border-slate-100 text-center">
            <p className="text-[11px] text-slate-400 flex items-center justify-center gap-1">
              <Lock className="w-3 h-3 text-slate-400" />
              <span>Role-scoped workspace separation & JWT session isolation</span>
            </p>
          </div>
        </div>
      </div>

      {/* Page Footer */}
      <footer className="w-full max-w-5xl mx-auto py-4 text-center text-xs text-slate-400">
        <span>© {new Date().getFullYear()} ContextFoundry Platform</span>
      </footer>
    </div>
  );
}
