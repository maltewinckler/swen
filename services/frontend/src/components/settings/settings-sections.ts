import { Bell, Brain, Download, Link as LinkIcon, Lock, Palette, User } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export type SettingsSectionId =
  | 'profile'
  | 'security'
  | 'connections'
  | 'ai'
  | 'exports'
  | 'notifications'
  | 'appearance'

export interface SettingsSection {
  id: SettingsSectionId
  icon: LucideIcon
  title: string
  description: string
}

export const SETTINGS_SECTIONS: SettingsSection[] = [
  {
    id: 'profile',
    icon: User,
    title: 'Profile',
    description: 'Manage your account details',
  },
  {
    id: 'security',
    icon: Lock,
    title: 'Security',
    description: 'Password and authentication',
  },
  {
    id: 'connections',
    icon: LinkIcon,
    title: 'Bank Connections',
    description: 'Manage linked bank accounts',
  },
  {
    id: 'ai',
    icon: Brain,
    title: 'AI Classification',
    description: 'Model and classification settings',
  },
  {
    id: 'exports',
    icon: Download,
    title: 'Data & Exports',
    description: 'Download your financial data',
  },
  {
    id: 'notifications',
    icon: Bell,
    title: 'Notifications',
    description: 'Configure alerts and reminders',
  },
  {
    id: 'appearance',
    icon: Palette,
    title: 'Appearance',
    description: 'Theme and display settings',
  },
]
