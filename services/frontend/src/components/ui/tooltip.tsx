import * as React from 'react'
import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import { cn } from '@/lib/utils'

export function TooltipProvider({ children }: { children: React.ReactNode }) {
  return <TooltipPrimitive.Provider>{children}</TooltipPrimitive.Provider>
}

export function Tooltip({
  children,
  delayDuration = 250,
}: {
  children: React.ReactNode
  delayDuration?: number
}) {
  return (
    <TooltipPrimitive.Root delayDuration={delayDuration}>
      {children}
    </TooltipPrimitive.Root>
  )
}

export const TooltipTrigger = TooltipPrimitive.Trigger

export function TooltipContent({
  children,
  className,
  sideOffset = 6,
}: {
  children: React.ReactNode
  className?: string
  sideOffset?: number
}) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          'z-[80] max-w-xs rounded-lg border border-border-subtle bg-bg-surface px-3 py-2 text-xs text-text-secondary shadow-lg',
          'data-[state=delayed-open]:animate-fade-in',
          className
        )}
      >
        {children}
        <TooltipPrimitive.Arrow className="fill-bg-surface" />
      </TooltipPrimitive.Content>
    </TooltipPrimitive.Portal>
  )
}
