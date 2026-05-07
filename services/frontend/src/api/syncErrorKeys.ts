// Map from backend ErrorCode values to i18n display strings
// (i18n layer is pending per AGENTS.md §4; strings are hardcoded for now)
const ERROR_KEY_MAP: Record<string, string> = {
  bank_connection_error: 'Verbindung zur Bank fehlgeschlagen',
  authentication_error: 'Authentifizierung fehlgeschlagen',
  tan_error: 'TAN-Eingabe fehlgeschlagen',
  internal_error: 'Interner Fehler',
  inactive_mapping: 'Konto-Zuordnung ist inaktiv',
  credentials_not_found: 'Keine Zugangsdaten gefunden',
  timeout_error: 'Zeitüberschreitung',
}

export function resolveErrorKey(errorKey: string): string {
  return ERROR_KEY_MAP[errorKey] ?? 'Synchronisierung fehlgeschlagen'
}
