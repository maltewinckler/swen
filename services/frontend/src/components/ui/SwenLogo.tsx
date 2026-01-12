import { cn } from '@/lib/utils'

interface SwenLogoProps {
  className?: string
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'hero'
}

const sizes = {
  sm: 'h-5 w-5',
  md: 'h-7 w-7',
  lg: 'h-12 w-12',
  xl: 'h-20 w-20',
  hero: 'h-32 w-32',
}

/**
 * SWEN Logo - Flow Balance
 *
 * Physics-inspired design representing equilibrium and conservation:
 * - Two curved flows meeting at a central balance point
 * - Symbolizes money flowing in and out in balance
 */
export function SwenLogo({ className, size = 'md' }: SwenLogoProps) {
  // Use thicker strokes for larger sizes
  const isLarge = size === 'xl' || size === 'hero'
  const strokeWidth = isLarge ? 4 : 3
  const endpointStroke = isLarge ? 2.5 : 2
  const centerRadius = isLarge ? 7 : 6
  const endpointRadius = isLarge ? 4 : 3

  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn(sizes[size], className)}
      aria-label="SWEN Logo"
    >
      {/* Subtle glow for hero size */}
      {size === 'hero' && (
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
      )}
      <g filter={size === 'hero' ? 'url(#glow)' : undefined}>
        {/* Left flow (income) */}
        <path
          d="M8 32 Q20 24 32 32"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          fill="none"
        />
        {/* Right flow (expense) */}
        <path
          d="M32 32 Q44 40 56 32"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          fill="none"
        />
        {/* Central balance point */}
        <circle cx="32" cy="32" r={centerRadius} fill="currentColor" />
        {/* Entry point */}
        <circle
          cx="8"
          cy="32"
          r={endpointRadius}
          stroke="currentColor"
          strokeWidth={endpointStroke}
          fill="none"
        />
        {/* Exit point */}
        <circle
          cx="56"
          cy="32"
          r={endpointRadius}
          stroke="currentColor"
          strokeWidth={endpointStroke}
          fill="none"
        />
      </g>
    </svg>
  )
}

