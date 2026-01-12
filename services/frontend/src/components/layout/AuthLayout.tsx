import { Outlet } from '@tanstack/react-router'
import { SwenLogo } from '@/components/ui'

export function AuthLayout() {
  return (
    <div className="min-h-screen bg-bg-base flex">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[80] focus:rounded-lg focus:bg-bg-surface focus:px-4 focus:py-2 focus:text-sm focus:text-text-primary focus:ring-2 focus:ring-accent-primary/50"
      >
        Skip to content
      </a>
      {/* Left side - branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-bg-surface via-bg-elevated to-bg-surface items-center justify-center p-12">
        <div className="max-w-md text-center animate-fade-in">
          {/* Logo with decorative ring */}
          <div className="relative mx-auto mb-8 w-fit">
            {/* Outer decorative ring */}
            <div className="absolute inset-0 -m-5 rounded-full border border-accent-primary/20" />
            {/* Middle ring with subtle pulse */}
            <div className="absolute inset-0 -m-2.5 rounded-full border border-accent-primary/10 animate-pulse" />
            {/* Logo */}
            <SwenLogo size="xl" className="text-accent-primary" />
          </div>
          <h1 className="text-4xl font-bold text-text-primary mb-2 tracking-tight">
            SWEN
          </h1>
          <p className="text-sm text-accent-primary/80 font-medium tracking-wide uppercase mb-6">
            Secure Wallet & Expense Navigator
          </p>
          <p className="text-lg text-text-secondary leading-relaxed">
            Your personal finance companion. Track expenses, sync bank accounts,
            and gain insights into your spending habits.
          </p>
          <div className="mt-10 flex items-center justify-center gap-6">
            <div className="text-center whitespace-nowrap">
              <div className="text-xl font-bold text-accent-success">Auto-Sync</div>
              <div className="text-sm text-text-muted">Bank Accounts</div>
            </div>
            <div className="h-10 w-px bg-border-subtle flex-shrink-0" />
            <div className="text-center whitespace-nowrap">
              <div className="text-xl font-bold text-accent-primary">Analytics</div>
              <div className="text-sm text-text-muted">& Insights</div>
            </div>
            <div className="h-10 w-px bg-border-subtle flex-shrink-0" />
            <div className="text-center whitespace-nowrap">
              <div className="text-xl font-bold text-chart-1">Privacy</div>
              <div className="text-sm text-text-muted">First</div>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - form */}
      <div
        id="main-content"
        tabIndex={-1}
        className="flex-1 flex items-center justify-center p-8 focus:outline-none"
      >
        <div className="w-full max-w-md animate-slide-up">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
