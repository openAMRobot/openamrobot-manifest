# Manifest state

OA-39 adds `releases/v2.0.0-rc.1.repos` alongside the unchanged development
manifest. All 11 repositories retain their paths and URLs and use full commit
SHAs. The 2026-10-19 snapshot agrees with the shared component revisions in
openamrobot-release PR #12. That builder also includes driver and governance
sources outside this development manifest's current scope.

The snapshot demonstrates a pinned checkout, not rc.1 acceptance. The final
release selection requires owner review and updates as outstanding fixes land.
OA-06 driver additions are separate; manifest PR #11 already proposes LiDAR
source selection, and PR #13 proposes CI image pinning. Neither is superseded.

Validation separates YAML/schema, immutable refs, source import, exact export,
package discovery and component builds. No hardware or safety implementation
is changed. Full workspace build and robot acceptance remain unverified here.
