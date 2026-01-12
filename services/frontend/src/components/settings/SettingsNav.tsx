import { ChevronRight } from 'lucide-react'
import { Card, CardContent } from '@/components/ui'
import { cn } from '@/lib/utils'
import type { SettingsSection, SettingsSectionId } from './settings-sections'

interface SettingsNavProps {
  sections: SettingsSection[]
  activeSection: SettingsSectionId | null
  onToggleSection: (sectionId: SettingsSectionId) => void
}

export function SettingsNav({ sections, activeSection, onToggleSection }: SettingsNavProps) {
  return (
    <Card>
      <CardContent className="p-2">
        <nav className="space-y-1">
          {sections.map((section) => (
            <button
              key={section.id}
              onClick={() => onToggleSection(section.id)}
              className={cn(
                'w-full flex items-center gap-3 p-3 rounded-lg transition-colors text-left',
                activeSection === section.id
                  ? 'bg-accent-primary/10 text-accent-primary'
                  : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
              )}
            >
              <section.icon className="h-5 w-5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{section.title}</p>
                <p className="text-xs text-text-muted truncate">{section.description}</p>
              </div>
              <ChevronRight
                className={cn('h-4 w-4 transition-transform', activeSection === section.id && 'rotate-90')}
              />
            </button>
          ))}
        </nav>
      </CardContent>
    </Card>
  )
}
