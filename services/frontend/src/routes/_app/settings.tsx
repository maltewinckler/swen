import { createFileRoute, useNavigate, useSearch } from '@tanstack/react-router'
import { useAuthStore } from '@/stores'
import {
  AISettingsSection,
  AppearanceSection,
  BankConnectionsSection,
  ExportsSection,
  NotificationsSection,
  ProfileSection,
  SecuritySection,
  SETTINGS_SECTIONS,
  SettingsNav,
  type SettingsSectionId,
} from '@/components/settings'

const SETTINGS_SECTION_IDS = new Set<SettingsSectionId>(SETTINGS_SECTIONS.map((s) => s.id))

export const Route = createFileRoute('/_app/settings')({
  component: SettingsPage,
  validateSearch: (search: Record<string, unknown>): { section: SettingsSectionId | null } => {
    const raw = typeof search.section === 'string' ? search.section : null
    const section = raw && SETTINGS_SECTION_IDS.has(raw as SettingsSectionId) ? (raw as SettingsSectionId) : null
    return { section }
  },
})

function SettingsPage() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const { section: activeSection } = useSearch({ from: '/_app/settings' })

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Page Header */}
      <div>
        <h1 className="text-display text-text-primary">Settings</h1>
        <p className="text-text-secondary mt-1">Manage your account and preferences</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Settings Navigation */}
        <div className="lg:col-span-1">
          <SettingsNav
            sections={SETTINGS_SECTIONS}
            activeSection={activeSection}
            onToggleSection={(sectionId) => {
              navigate({
                to: '/settings',
                search: { section: activeSection === sectionId ? null : sectionId },
                replace: true,
              })
            }}
          />
        </div>

        {/* Settings Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Profile Section */}
          {(activeSection === 'profile' || activeSection === null) && <ProfileSection user={user} />}

          {/* Security Section */}
          {activeSection === 'security' && <SecuritySection />}

          {/* Bank Connections Section */}
          {activeSection === 'connections' && (
            <BankConnectionsSection onGoToAccounts={() => navigate({ to: '/accounts' })} />
          )}

          {/* Data & Exports Section */}
          {activeSection === 'exports' && <ExportsSection />}

          {/* Notifications Section */}
          {activeSection === 'notifications' && <NotificationsSection />}

          {/* AI Section */}
          {activeSection === 'ai' && <AISettingsSection />}

          {/* Appearance Section */}
          {activeSection === 'appearance' && <AppearanceSection />}
        </div>
      </div>
    </div>
  )
}
