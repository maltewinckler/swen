import { api } from './client'

// =============================================================================
// Types
// =============================================================================

export interface CompletedSteps {
  accounts_initialized: boolean
  first_bank_connected: boolean
  has_transactions: boolean
}

export interface OnboardingStatus {
  needs_onboarding: boolean
  completed_steps: CompletedSteps
}

// =============================================================================
// Onboarding API
// =============================================================================

/**
 * Get onboarding status for the current user.
 *
 * The status is derived from existing data:
 * - accounts_initialized: True if expense accounts exist
 * - first_bank_connected: True if bank credentials exist
 * - has_transactions: True if transactions exist
 */
export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  return api.get<OnboardingStatus>('/onboarding/status')
}

