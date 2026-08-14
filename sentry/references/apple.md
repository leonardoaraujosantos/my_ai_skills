# Sentry — Apple (iOS, macOS, tvOS, watchOS, visionOS)

Docs: https://docs.sentry.io/platforms/apple/guides/ios/ (append `.md` for Markdown).

Captures errors, **crashes**, watchdog terminations, and app hangs — the last two are
Apple-specific and the main reason to use this SDK over generic logging.

## Install — use the wizard

```bash
brew install getsentry/tools/sentry-wizard && sentry-wizard -i ios
```

The wizard:

- adds the SDK via Swift Package Manager,
- patches `AppDelegate` / the SwiftUI `App` initializer with a default config and a
  sample error,
- adds an **Upload Debug Symbols** build phase to `xcodebuild`,
- creates `.sentryclirc` with an auth token (auto-added to `.gitignore`),
- adds a Fastlane lane for dSYM upload if Fastlane is present.

Patch once, commit the patched files. The debug-symbol build phase is the part worth
having — hand-rolling it is where manual setups go wrong.

Manual alternative: SPM `https://github.com/getsentry/sentry-cocoa`, CocoaPods
`pod 'Sentry'`, or Carthage. See
https://docs.sentry.io/platforms/apple/guides/ios/manual-setup.md.

## Init — main thread, as early as possible

### Swift (UIKit)

```swift
import Sentry

func application(_ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {

    SentrySDK.start { options in
        options.dsn = "https://<key>@o<orgId>.ingest.sentry.io/<projectId>"
        options.debug = true // Enabled debug when first installing is always helpful

        // Adds IP for users.
        options.sendDefaultPii = true

        // Set tracesSampleRate to 1 to capture 100% of transactions for performance monitoring.
        // We recommend adjusting this value in production.
        options.tracesSampleRate = 1

        options.configureProfiling = {
            $0.lifecycle = .trace
            $0.sessionSampleRate = 1
        }

        // Record session replays for 100% of errors and 10% of sessions
        options.sessionReplay.onErrorSampleRate = 1.0
        options.sessionReplay.sessionSampleRate = 0.1

        // Enable logs to be sent to Sentry
        options.enableLogs = true
    }

    return true
}
```

### SwiftUI

```swift
import Sentry

@main
struct SwiftUIApp: App {
    init() {
        SentrySDK.start { options in
            options.dsn = "https://<key>@o<orgId>.ingest.sentry.io/<projectId>"
            options.debug = true
            options.sendDefaultPii = true
            options.tracesSampleRate = 1
            options.configureProfiling = {
                $0.lifecycle = .trace
                $0.sessionSampleRate = 1
            }
            options.sessionReplay.onErrorSampleRate = 1.0
            options.sessionReplay.sessionSampleRate = 0.1
            options.enableLogs = true
        }
    }
}
```

### Objective-C

```objc
@import Sentry;

- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)launchOptions {

    [SentrySDK startWithConfigureOptions:^(SentryOptions *options) {
        options.dsn = @"https://<key>@o<orgId>.ingest.sentry.io/<projectId>";
        options.debug = YES;
        options.sendDefaultPii = YES;
        options.tracesSampleRate = @1.f;
        options.configureProfiling = ^(SentryProfileOptions *profiling) {
            profiling.lifecycle = SentryProfileLifecycleTrace;
            profiling.sessionSampleRate = 1.f;
        };
        options.sessionReplay.onErrorSampleRate = 1.0;
        options.sessionReplay.sessionSampleRate = 0.1;
        options.enableLogs = YES;
    }];

    return YES;
}
```

Production adjustments to the wizard defaults: `debug = false`,
`tracesSampleRate = 0.1`, `sessionSampleRate` for replay `0.01–0.1`, and set
`options.environment` / `options.releaseName` from the build configuration rather than
letting them default.

**Initializing off the main thread is possible but not recommended** — some setup
(view hierarchy collection) still needs the main thread, and main-thread init is what
makes launch-crash detection reliable.

## Verify

```swift
import Sentry

do {
    try aMethodThatMightFail()
} catch {
    SentrySDK.capture(error: error)
}
```

```objc
@import Sentry;

NSError *error = nil;
[self aMethodThatMightFail:&error]

if (error) {
    [SentrySDK captureError:error];
}
```

**Crashes only report with the debugger detached.** Run the app from the home screen
(stop the Xcode session first), crash it, then relaunch — the crash is sent on the next
launch, not at crash time. Expect a couple of minutes before it appears.

## dSYMs — without these, every crash is hex addresses

Three ways, pick one:

1. **Build phase (wizard default)** — a `Run Script` phase calling
   `sentry-cli debug-files upload` on `$DWARF_DSYM_FOLDER_PATH`. Requires
   `DEBUG_INFORMATION_FORMAT = DWARF with dSYM File` for **Release** (and for Debug if
   you want symbolicated dev crashes).
2. **Fastlane** — the wizard's lane, or `sentry_cli` action after `gym`.
3. **Bitcode/App Store recompilation** — if the App Store re-signs or recompiles, the
   dSYMs you built locally don't match. Download the App Store Connect dSYMs and
   upload those: `sentry-cli debug-files upload --include-sources <path>`.

Verify in the UI under **Settings → Projects → <project> → Debug Files**; the UUID in a
crash's image list must appear there. See `operations.md` for the CLI commands.

## Source context

Uploading with `--include-sources` embeds source snippets so stack frames show your
actual code lines. Worth it for a private app; skip if you don't want source on
Sentry's servers.
See https://docs.sentry.io/platforms/apple/guides/ios/sourcecontext.md.

## Privacy manifest

Apple requires a `PrivacyInfo.xcprivacy` declaring required-reason API use. Sentry
publishes the entries to merge:
https://docs.sentry.io/platforms/apple/guides/ios/data-management/apple-privacy-manifest.md.
Missing entries get builds rejected at App Store submission, so do this before the
first upload rather than during a release scramble.

## Other Apple targets

Same SDK, different guide pages: `macos`, `tvos`, `watchos`, `visionos` under
`https://docs.sentry.io/platforms/apple/guides/<target>/`. watchOS has no session
replay; visionOS profiling support lags.

## Useful extras

- **App hangs / ANR**: on by default, reported as their own issue type. Tune with
  `options.appHangTimeoutInterval`.
- **Watchdog terminations**: reported heuristically on next launch; expect some noise
  from users force-quitting.
- **View hierarchy & screenshots on error**:
  `options.attachScreenshot = true`, `options.attachViewHierarchy = true`.
  Screenshots can contain PII — treat them as customer data.
- **User feedback widget**:
  https://docs.sentry.io/platforms/apple/guides/ios/user-feedback.md.
