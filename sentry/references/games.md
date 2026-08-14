# Sentry — Unity and Unreal Engine

Game engines differ from app SDKs in two ways that matter: the DSN lives in an **asset
or config file** committed to the repo (not an env var), and crash reporting depends on
**minidumps + debug symbols per platform**, which must be uploaded per build.

---

## Unity

Docs: https://docs.sentry.io/platforms/unity/

### Install

Unity Package Manager → **Add package from git URL**:

```
https://github.com/getsentry/unity.git
```

Append a tag to pin a version, e.g. `https://github.com/getsentry/unity.git#4.8.0`.
Pin it — an unpinned git dependency will silently move under your team.

Also available as a `.unitypackage` from the GitHub Releases page for projects that
don't use UPM git dependencies.

### Configure

1. Unity menu: **Tools → Sentry** opens the setup wizard.
2. Paste the DSN:
   ```json
   {
     "public-dsn": "https://<key>@o<orgId>.ingest.sentry.io/<projectId>"
   }
   ```
3. Config is stored at `Assets/Resources/Sentry/SentryOptions.asset` — **commit it**;
   the build reads it at runtime.
4. Remaining options (sample rates, environment, release, debug logging, IL2CPP line
   numbers, native support per platform) live in the same editor window.

For per-environment DSNs, override programmatically at startup:

```csharp
using Sentry.Unity;

public static class SentryInitialization
{
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
    public static void Init()
    {
        SentryUnity.Init(options =>
        {
            options.Dsn = BuildConfig.SentryDsn;
            options.Environment = Debug.isDebugBuild ? "development" : "production";
            options.Release = Application.version;
            options.TracesSampleRate = 0.1f;
            options.Debug = Debug.isDebugBuild;
        });
    }
}
```

`SubsystemRegistration` runs before the first scene loads, which is early enough to
catch startup errors.

### Verify

Attach a MonoBehaviour that throws on `Start()` (e.g. a deliberate
`NullReferenceException`), run the build, and check the issue in sentry.io. Unity's own
console logging is forwarded as breadcrumbs, so the issue arrives with the log tail.

### Symbols

- **IL2CPP**: enable line-number support in the Sentry editor window and let the SDK's
  build post-processor upload symbols; otherwise C# frames come back as native
  addresses.
- **Android/iOS builds** need the same native symbol upload as a normal app (see
  `android.md` / `apple.md`) — the Unity SDK hooks the build to do it when you supply
  org/project/auth token in the editor window.
- Auth token goes in the editor config which is **gitignored** by the SDK's own
  `.gitignore` entry; in CI supply `SENTRY_AUTH_TOKEN`.

---

## Unreal Engine

Docs: https://docs.sentry.io/platforms/unreal/

### Install

Download the latest plugin from the
[GitHub Releases page](https://github.com/getsentry/sentry-unreal/releases) (recommended
over the marketplace/Fab copy, which lags) and extract into your project's `Plugins/`
directory.

The SDK requires a **C++ project**. Blueprint-only projects work once you add any empty
C++ class to generate the build files.

Enable under **Settings → Plugins → Code Plugins**, then add the module dependency in
`MyProject.build.cs`:

```csharp
PublicDependencyModuleNames.AddRange(new string[] { ..., "Sentry" });
```

### Configure

**Project Settings → Plugins → Sentry**. Minimum is the DSN:

```json
{
  "public-dsn": "https://<key>@o<orgId>.ingest.sentry.io/<projectId>"
}
```

The SDK auto-initializes on startup by default. To control it (e.g. per-environment
DSN, opt-in consent flow), disable auto-init in project settings and call
`InitializeWithSettings` at runtime.

### Verify

```cpp
#include "SentrySubsystem.h"

void Verify()
{
    USentrySubsystem* SentrySubsystem = GEngine->GetEngineSubsystem<USentrySubsystem>();
    SentrySubsystem->CaptureMessage(TEXT("Capture message"));
}
```

Every function is also exposed to Blueprints via the same subsystem node.

### Crashes and minidumps

- **Windows, UE 5.1 and older**: configure the Crash Reporter Client explicitly
  (`CrashReportClient` ini settings pointing at Sentry).
- **UE 5.2+**: you can switch between the default UE crash handler and the Sentry
  handler via the API — they are **mutually exclusive**, so pick one.
- Minidump storage must be enabled in Sentry: **Organization/Project Settings →
  Security & Privacy**. Supported for Windows, Linux, and Android.
- Upload debug symbols (`.pdb`, `.dSYM`, `.so`) per packaged build; the plugin can do
  it automatically when given org/project/auth token in project settings, otherwise:
  ```bash
  sentry-cli debug-files upload --include-sources <path-to-packaged-build>
  ```

### Gotchas

- Editor-launched play sessions and packaged builds behave differently — always verify
  against a **packaged** build.
- Console platforms (PS/Xbox/Switch) need the private, NDA-gated plugin variants;
  the public plugin covers Windows, Mac, Linux, Android, iOS.
- Crash reports arrive on the *next* launch of the game, not at crash time.
