import { Link, useRouter } from '@tanstack/react-router'
import {
  LayoutDashboard,
  ArrowLeftRight,
  Wallet,
  Settings,
  LogOut,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores'
import { Button, SwenLogo } from '@/components/ui'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/transactions', label: 'Transactions', icon: ArrowLeftRight },
  { to: '/accounts', label: 'Accounts', icon: Wallet },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const

export function Navbar() {
  const { user, logout } = useAuthStore()
  const router = useRouter()

  const handleLogout = async () => {
    await logout()
    router.navigate({ to: '/login' })
  }

  return (
    <>
      {/* Desktop Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border-subtle bg-bg-surface/80 backdrop-blur-sm">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-2 text-text-primary">
            <SwenLogo size="md" className="text-accent-primary" />
            <span className="text-lg font-semibold tracking-tight">SWEN</span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg',
                  'transition-colors duration-fast',
                  'text-text-secondary hover:text-text-primary hover:bg-bg-hover',
                  '[&.active]:text-text-primary [&.active]:bg-bg-hover'
                )}
              >
                <item.icon className="h-4 w-4" />
                <span>{item.label}</span>
              </Link>
            ))}
          </nav>

          {/* User Menu */}
          <div className="flex items-center gap-4">
            {user && (
              <span className="hidden sm:block text-sm text-text-secondary">
                {user.email}
              </span>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              aria-label="Logout"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-bg-surface border-t border-border-subtle safe-area-bottom">
        <div className="flex items-center justify-around h-16">
          {navItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                'flex flex-col items-center justify-center flex-1 h-full',
                'text-text-secondary transition-colors',
                '[&.active]:text-accent-primary'
              )}
            >
              <item.icon className="h-5 w-5" />
              <span className="text-xs mt-1">{item.label}</span>
            </Link>
          ))}
        </div>
      </nav>
    </>
  )
}
