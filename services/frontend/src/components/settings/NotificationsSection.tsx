/**
 * Notifications Section
 *
 * Placeholder for notification preferences (coming soon).
 */

import { Bell } from 'lucide-react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui'

export function NotificationsSection() {
  return (
    <Card className="animate-slide-up">
      <CardHeader>
        <CardTitle>Notification Preferences</CardTitle>
        <CardDescription>Configure when and how you receive alerts</CardDescription>
      </CardHeader>
      <CardContent className="text-center py-8">
        <Bell className="h-12 w-12 text-text-muted mx-auto mb-4" />
        <p className="text-text-secondary">Notification settings coming soon</p>
      </CardContent>
    </Card>
  )
}
