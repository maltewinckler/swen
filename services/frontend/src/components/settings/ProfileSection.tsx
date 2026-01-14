/**
 * Profile Section
 *
 * Displays user profile information in the settings page.
 */

import { ShieldCheck, User as UserIcon } from 'lucide-react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  FormField,
  Input,
  Badge,
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
        <FormField label="Role">
          <div className="flex items-center h-10">
            {user?.role === 'admin' ? (
              <Badge variant="warning">
                <ShieldCheck className="h-3 w-3 mr-1" />
                Administrator
              </Badge>
            ) : (
              <Badge variant="default">
                <UserIcon className="h-3 w-3 mr-1" />
                User
              </Badge>
            )}
          </div>
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
