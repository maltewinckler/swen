/**
 * Appearance Section
 *
 * Placeholder for theme customization (coming soon).
 */

import { Palette } from 'lucide-react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui'

export function AppearanceSection() {
  return (
    <Card className="animate-slide-up">
      <CardHeader>
        <CardTitle>Appearance</CardTitle>
        <CardDescription>Customize how SWEN looks</CardDescription>
      </CardHeader>
      <CardContent className="text-center py-8">
        <Palette className="h-12 w-12 text-text-muted mx-auto mb-4" />
        <p className="text-text-secondary">Theme customization coming soon</p>
      </CardContent>
    </Card>
  )
}

