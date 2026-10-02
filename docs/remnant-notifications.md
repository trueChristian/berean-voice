# Remnant website publication notifications

These notification hooks run automatically when `REMNANT_DISPATCH_TOKEN` is
configured. They request a rebuild in
[`trueChristian/remnant.truechristian.church`](https://github.com/trueChristian/remnant.truechristian.church)
only after a successfully validated, durably published display snapshot changes.
The website receives `remnant-content-updated`, resolves current trusted source
branches, and revalidates exports. No article wording, translation policy, or
publication status is changed by this integration.

The receiving workflow lives in the website repository. Its publication contract
is recorded in [website issue #1](https://github.com/trueChristian/remnant.truechristian.church/issues/1).

## Token-only configuration

`REMNANT_DISPATCH_TOKEN` is the only configuration prerequisite. There is no
separate enablement variable. Existing configured tokens are used automatically;
no credential changes are required by this code change.

1. Securely configure `REMNANT_DISPATCH_TOKEN` as a repository Actions secret.
   Use an approved GitHub App installation token or fine-grained credential
   restricted to **the website repository only**, with `Contents: write`, as
   required by GitHub's repository-dispatch endpoint. Prefer a maintained GitHub
   App flow; short-lived tokens need an independently approved renewal/minting
   setup. An ordinary source-repository `GITHUB_TOKEN` cannot dispatch to another
   repository. This change does not create credentials or configure access.
2. The next successful trusted main publication workflow described below checks
   token presence and attempts notification when the display changes. A missing
   token produces a warning and job summary, then skips delivery. Inspect its notification
   result, then verify the receiving website build separately. No source workflow
   deploys the website.

Never paste credentials into a pull request, issue, artifact, file, or command
argument. The helper reads the token only from the step environment, sends it
only to the fixed GitHub repository-dispatch API endpoint, refuses redirects,
and suppresses private response bodies and exception details.

## Delivery and recovery

The public-display fingerprint includes exported metadata, article HTML and
images. Generated manifests and revision-only metadata are excluded, so internal
checkpoints do not cause repeated notifications. Translation notifications also
fingerprint the language registry's public names, tags, direction and aliases;
internal translation guidance and runtime records are excluded. New zero-article
locales therefore request a website interface-validation build.

A restored Actions cache remembers the last accepted fingerprint. The helper
checks clean source inputs, an export manifest matching HEAD, and HEAD equal to
current remote `main` before sending. Only HTTP 204 saves a success marker. A
rejected/failed/uncertain request leaves the old marker in place. GitHub API errors
report only the HTTP status and safe troubleshooting guidance, never the token or
private response details. Token presence does not prove its validity. Cache loss can
cause a safe duplicate. If a newer source commit arrives while checking, rerun
against current main instead of notifying a stale revision.

Notification acceptance is not proof of website deployment. Inspect the website
workflow separately; it owns coalescing, duplicate-output handling and recovery.
After a failed notification, correct the setup/connectivity problem and rerun the
trusted source workflow. To force a website recovery when a previously accepted
notification did not produce a deployment, use the website's manual build flow.

## Offline tests

`python3 -m unittest discover -s tests -v` includes mocked notification tests. They
never send a real dispatch, use real credentials, or start paid translation work.
The copied `.github/remnant/dispatch.py` and `validate_event.py` share the versioned
website event contract. Keep them synchronized with the website implementation
when that contract changes.

References: [GitHub token behavior](https://docs.github.com/en/actions/concepts/security/github_token)
and [repository dispatch permissions](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event).

## English publishing path

`Archive contract` notifies only on trusted `main`, after the full archive
validation, regression suite, deterministic projection checks, and both supported
export base-path checks pass. A fresh root-domain export is fingerprinted. New
English content never waits for translations. Pull-request validation cannot
enter the notification steps. For recovery, rerun `Archive contract` on `main`.
