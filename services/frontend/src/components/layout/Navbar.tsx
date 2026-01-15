import { Link, useRouter } from '@tanstack/react-router'
import {
  LayoutDashboard,
  ArrowLeftRight,
  Wallet,
  Settings,
  LogOut,
  User,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores'
import {
  SwenLogo,
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/transactions', label: 'Transactions', icon: ArrowLeftRight },
  { to: '/accounts', label: 'Accounts', icon: Wallet },
] as const

function UserAvatar({ email, size = 'md' }: { email: string; size?: 'sm' | 'md' }) {
  const initials = email
    .split('@')[0]
    .slice(0, 2)
    .toUpperCase()

  return (
    <div
      className={cn(
        'flex items-center justify-center rounded-full bg-bg-hover text-text-secondary font-medium border border-border-subtle',
        size === 'sm' ? 'h-7 w-7 text-xs' : 'h-9 w-9 text-sm'
      )}
    >
      {initials}
    </div>
  )
}

function UserDropdownContent({ onLogout }: { onLogout: () => void }) {
  return (
    <>
      <DropdownMenuItem asChild>
        <Link to="/settings" search={{ section: null }} className="flex items-center gap-2 cursor-pointer">
          <Settings className="h-4 w-4" />
          Settings
        </Link>
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem
        onClick={onLogout}
        className="text-accent-danger focus:text-accent-danger"
      >
        <LogOut className="h-4 w-4" />
        Logout
      </DropdownMenuItem>
    </>
  )
}

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

          {/* User Menu (Desktop) */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className={cn(
                  'rounded-full',
                  'transition-all duration-fast',
                  'hover:ring-2 hover:ring-accent-primary/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/50'
                )}
                aria-label="Account menu"
              >
                {user && <UserAvatar email={user.email} />}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              {user && (
                <>
                  <DropdownMenuLabel className="font-normal">
                    <div className="flex flex-col space-y-1">
                      <p className="text-sm font-medium text-text-primary">{user.email}</p>
                      <p className="text-xs text-text-muted">Manage your account</p>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                </>
              )}
              <UserDropdownContent onLogout={handleLogout} />
            </DropdownMenuContent>
          </DropdownMenu>
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

          {/* Mobile User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className={cn(
                  'flex flex-col items-center justify-center flex-1 h-full',
                  'text-text-secondary transition-colors',
                  'focus:outline-none'
                )}
              >
                {user ? (
                  <>
                    <UserAvatar email={user.email} size="sm" />
                    <span className="text-xs mt-1">Account</span>
                  </>
                ) : (
                  <>
                    <User className="h-5 w-5" />
                    <span className="text-xs mt-1">Account</span>
                  </>
                )}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" side="top" sideOffset={8} className="w-56">
              {user && (
                <>
                  <DropdownMenuLabel className="font-normal">
                    <div className="flex flex-col space-y-1">
                      <p className="text-sm font-medium text-text-primary">{user.email}</p>
                      <p className="text-xs text-text-muted">Manage your account</p>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                </>
              )}
              <UserDropdownContent onLogout={handleLogout} />
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </nav>
    </>
  )
}
