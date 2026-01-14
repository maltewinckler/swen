import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'link'
  size?: 'sm' | 'md' | 'lg' | 'icon'
  isLoading?: boolean
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({
    className,
    variant = 'primary',
    size = 'md',
    isLoading = false,
    asChild = false,
    children,
    disabled,
    ...props
  }, ref) => {
    const Comp = asChild ? Slot : 'button'

    const variants = {
      primary: 'bg-accent-primary text-white hover:bg-accent-primary/90 active:scale-[0.98]',
      secondary: 'bg-transparent border border-border-default text-text-primary hover:bg-bg-hover hover:border-border-focus active:scale-[0.98]',
      ghost: 'bg-transparent text-text-secondary hover:text-text-primary hover:bg-bg-hover',
      danger: 'bg-accent-danger text-white hover:bg-accent-danger/90 active:scale-[0.98]',
      link: 'bg-transparent text-accent-primary hover:underline underline-offset-4',
    }

    const sizes = {
      sm: 'h-8 px-3 text-sm rounded-md gap-1.5',
      md: 'h-10 px-4 text-sm rounded-lg gap-2',
      lg: 'h-12 px-6 text-base rounded-lg gap-2',
      icon: 'h-10 w-10 rounded-lg',
    }

    return (
      <Comp
        className={cn(
          'inline-flex items-center justify-center font-medium transition-all duration-fast cursor-pointer',
          'disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none',
          variants[variant],
          sizes[size],
          className
        )}
        ref={ref}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>{children}</span>
          </>
        ) : (
          children
        )}
      </Comp>
    )
  }
)
Button.displayName = 'Button'

export { Button }
