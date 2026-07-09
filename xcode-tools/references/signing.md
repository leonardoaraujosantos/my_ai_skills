# Code Signing Triage

## Inventory

```bash
security find-identity -v -p codesigning
# → 1) <40-hex SHA-1> "Apple Development: Name (TEAMID)" … "N valid identities found"
```

`0 valid identities found` = certificate missing, expired, or its **private key**
is absent from the keychain (the most common CI case).

## Provisioning profiles

Locations (check both — moved in Xcode 16):
- `~/Library/Developer/Xcode/UserData/Provisioning Profiles/` (Xcode 16+)
- `~/Library/MobileDevice/Provisioning Profiles/` (pre-16 tools still write here)

```bash
security cms -D -i profile.mobileprovision | plutil -p -          # decode
security cms -D -i profile.mobileprovision | plutil -extract Entitlements xml1 -o - -
```

Key fields: `UUID`, `Name`, `TeamIdentifier`, `ExpirationDate`,
`ProvisionedDevices`, `DeveloperCertificates` (DER — match against your local
cert: `openssl x509 -inform DER -noout -fingerprint -sha1`),
`Entitlements.application-identifier`, `get-task-allow` (true = development
profile), `ProvisionsAllDevices` (enterprise).

Inspect what a binary was actually signed with:

```bash
codesign -dv --entitlements - MyApp.app     # authority chain, TeamID, entitlements
codesign --verify --deep --strict MyApp.app
```

## Error → fix table

| Error | Cause → fix |
|-------|-------------|
| "No signing certificate 'iOS Development' found" | Cert not in (this) keychain. `security find-identity`; re-download from ASC or let `-allowProvisioningUpdates` mint one |
| "…doesn't match any valid certificate/private key pair" | Cert present, **private key missing** (imported .cer without .p12). Import the .p12: `security import cert.p12 -k build.keychain -P "$P12_PW" -T /usr/bin/codesign` |
| "Provisioning profile …doesn't include signing certificate" | Profile generated against a different cert — regenerate on the portal or `-allowProvisioningUpdates` |
| "Profile doesn't support/include the X entitlement" | App ID capabilities out of sync — fix capabilities on the portal, regenerate profile; diff `codesign -d --entitlements -` vs the profile's `Entitlements` dict |
| `errSecInternalComponent` during CI signing | Keychain locked or missing partition list — see recipe below |
| Signs locally, fails in CI | CI uses a different keychain/keychain search list — see recipe below |

Automatic signing = `CODE_SIGN_STYLE=Automatic` + `DEVELOPMENT_TEAM=TEAMID` +
`-allowProvisioningUpdates` (headless portal auth via
`-authenticationKeyPath/-authenticationKeyID/-authenticationKeyIssuerID`).
Manual = `CODE_SIGN_STYLE=Manual` + `PROVISIONING_PROFILE_SPECIFIER="Name"` +
`CODE_SIGN_IDENTITY="Apple Distribution"`.

## CI temp-keychain recipe (the standard)

```bash
security create-keychain -p "$PW" build.keychain
security set-keychain-settings -lut 21600 build.keychain      # no auto-lock for 6h
security unlock-keychain -p "$PW" build.keychain
security import cert.p12 -k build.keychain -P "$P12_PW" \
  -T /usr/bin/codesign -T /usr/bin/security
# Critical line — without it codesign hangs on a UI permission prompt:
security set-key-partition-list -S apple-tool:,apple: -s -k "$PW" build.keychain
security list-keychains -d user -s build.keychain login.keychain
```

Team alternative: fastlane **match** stores encrypted certs+profiles in
git/S3/GCS and installs them reproducibly (`fastlane match appstore`) — see
mobile-publish for fastlane state.
