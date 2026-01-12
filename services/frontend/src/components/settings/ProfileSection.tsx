/**
 * Profile Section
 *
 * Displays user profile information in the settings page.
 */

import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  FormField,
  Input,
} from '@/components/ui'
import type { UserInfo } from '@/types/api'
import { formatDate } from '@/lib/utils'

interface ProfileSectionProps {
  user: UserInfo | null
}

export function ProfileSection({ user }: ProfileSectionProps) {
  return (
    <Card className="animate-slide-up">
      <CardHeader>
        <CardTitle>Profile Information</CardTitle>
        <CardDescription>Your account details</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormField label="Email">
          <Input value={user?.email ?? ''} disabled />
        </FormField>
        <FormField label="Member since">
          <Input
            value={user?.created_at ? formatDate(user.created_at) : ''}
            disabled
          />
        </FormField>
      </CardContent>
    </Card>
  )
}
