# FinTS Credentials

To connect SWEN to your German bank you need two things from Deutsche Kreditwirtschaft:

1. A **FinTS Product ID** (a short alphanumeric code)
2. The **bank directory CSV** (`fints_institute.csv`) listing all participating banks

Both are configured through the SWEN admin UI — no config file editing needed after the initial setup.

## Why You Need a Product ID

The German banking industry (Deutsche Kreditwirtschaft) requires all FinTS software to be registered. This requirement has been in force since 2020. Banks will reject connections from unregistered software.

The registration is **free** and typically approved within a few business days.

## Registering

1. Go to [fints.org/de/hersteller/produktregistrierung](https://www.fints.org/de/hersteller/produktregistrierung)
2. Fill out the form:
   - **Produktname**: e.g. "SWEN Personal Finance"
   - **Produktversion**: `0.1`
   - **Hersteller**: your name or organisation
   - **Produktart**: "Privatanwender-Software" works fine for self-hosted use
3. Submit — you will receive a confirmation email with your **Product ID** and a **CSV file** of bank routing data

## Configuring in SWEN

Once SWEN is running:

1. Log in as an admin user
2. Go to **Settings → Administration → FinTS Configuration**
3. Enter your **Product ID**
4. Upload the **institute CSV** (`fints_institute.csv`)

<!-- SCREENSHOT: settings-fints.png — FinTS configuration section in Settings -->
![FinTS Settings](../assets/screenshots/settings-fints.png)

After saving, go to **Bank Accounts → Add Bank Account** to connect your first account.

## Supported TAN Methods

SWEN currently supports the **decoupled push-TAN** method (used by apps like SecureGo, ING App, DKB App, Sparkasse App). The workflow is:

1. SWEN initiates the FinTS request
2. Your banking app sends a push notification
3. You approve in the app
4. SWEN polls for confirmation and completes the request

!!! warning "Not all TAN methods tested"
    While the decoupled method works with most German banks that offer it, other TAN methods (chipTAN, smsTAN, etc.) have not been thoroughly tested. If you encounter a problem, please open a GitHub issue.

## Finding Your Bank

Not all German banks support FinTS. Check the [Subsembly bank list](https://subsembly.com/banken.html) for an (admittedly outdated) overview of supported banks and their BLZ.

## Known Limitations

### Visa Debit IBAN Ambiguity

Some banks (notably ING) issue a separate IBAN for Visa Debit transactions that differs from your main IBAN. When mapping bank accounts in SWEN, you may see two accounts with very similar names. The correct one to use is your **main GIRO IBAN** — the Visa Debit transactions will still appear under the same account in most bank FinTS implementations.

### TAN Timeout

FinTS TAN requests expire after ~120 seconds. If you do not approve the push notification in time, the import fails silently. Simply retry the sync — no data is lost.

### Rate Limiting

Most banks limit FinTS requests to a few per minute. SWEN respects this by not parallelising bank requests.
