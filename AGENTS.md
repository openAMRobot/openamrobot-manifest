<!-- BEGIN OPENAMROBOT SHARED RULES v1 -->
# OpenAMRobot agent rules
Canonical shared block: openAMRobot/.github, agent-rules/SHARED_RULES.md.
This block is copied verbatim; GitHub does not propagate it between repositories.

## Before editing
- Read AGENTS.md, CONTRIBUTING.md, applicable nested instructions, code and tests.
- Record the base SHA; inspect relevant open PRs and accessible branches/forks for overlap.
- Do not infer contributor inactivity from absent public branches; disclose inaccessible work.
- Follow the approved task scope and applicable plan/contracts. Report contradictions.
- Reuse maintained upstream packages and existing implementation; minimize custom glue.
- Do not replace working legacy support merely because the new-robot BOM excludes it.

## Boundaries
- Shared ROS contracts belong in openamrobot-interfaces; identify their actual acceptance status.
- New contract proposals stay isolated and labelled Proposed, pending owner review.
- Do not author or modify safety implementation: E-stop, brakes, motion interlocks,
  watchdogs, actuator enable or power-protection logic. Report required changes.
- Status display and isolated test fixtures do not implement or validate physical safety.
- Arm vendor SDKs stay behind Device Packages; none in UI or mission consumers.
- Preserve Gate A Teensy/MPU6500 and Gate B STM32/ICM-42688-P distinctions.
- Jetson is the 2.0 reference compute; retain correctly labelled historical material.
- Public application name: Use_Case_1. No customer/partner names, secrets or private data.
- Preserve third-party provenance. Do not change licensing, NOTICE or CODEOWNERS
  without an explicit task that authorizes those files and the appropriate review.
- Never connect untrusted/automated PR tests to physical motion hardware or secrets.

## Delivery
- Use a contributor branch/fork and draft PR by default. Never merge, force-push,
  modify protection/settings or bypass checks in ordinary implementation tasks.
- Read applicable CLA/DCO rules. Never invent an exemption, identity or attestation.
- Use git commit -s only with the verified contributor identity and provenance authority.
- Disclose material AI assistance, dependencies and licence implications.
- Report base/head SHAs, scope, safety impact, exact commands/results and evidence links.
- For bug fixes show the regression fails before and passes after; for new features
  demonstrate a meaningful deliberate fault is detected. Explain non-applicability.
- Keep a Not verified section. SKIP/BLOCKED is not PASS; fixtures/fake hardware are
  not integrated simulation, physical acceptance or release readiness.
- Do not weaken checks, use empty suites as evidence or invent successful test results.
- If blocked, stop the blocked activity, report command/error/next step and continue
  independent in-scope work. Do not repeatedly reinstall or expand the architecture.
- Owner alignment and approval status must be truthful. A draft or notification is
  not evidence that a required discussion or technical acceptance has happened.
<!-- END OPENAMROBOT SHARED RULES v1 -->

# Repository-specific rules: openamrobot-manifest
## Ownership and boundaries
- This repository owns workspace repository selection and version references.
- Karthikeyan handles install/release work; Arumuga reviews CI conventions.
- Development manifests may track branches. Release manifests require immutable refs.
- Preserve checkout paths and branch selections in syntax-only fixes.
- Do not describe import, package discovery and build as equivalent checks.

## Verification
- With vcstool installed: vcs validate < openamrobot.repos
- With yamllint installed: yamllint -d '{extends: relaxed, rules: {key-duplicates: enable, line-length: disable}}' openamrobot.repos
- Alternatively use a tested strict YAML loader; plain safe_load accepts duplicates.
- In a fresh temporary workspace: vcs import . < /absolute/path/openamrobot.repos
- Record resolved revisions with vcs export --exact . and inspect colcon list output.
- Run colcon list at workspace root, and report packages outside src/; do not hide
  them by silently changing README instructions or adding COLCON_IGNORE files.
- A network/authentication failure is a blocked import, not an invalid YAML result.
- Follow existing reusable CI when capable; otherwise use a small temporary local
  gate with the same local command and an explicit migration note for Arumuga.

## Canonical context
- [Plans](https://drive.google.com/drive/folders/15zWoBPd6qSt96TToWakN9rhfjNyq-hoz)
- [D-02 AI framework](https://drive.google.com/file/d/1Drs4tKbxAo6jsRlaCRK1eAMkzds7NTx-/view)
- [D-03 consistency](https://drive.google.com/file/d/1jbELSAeWRxuxB-IO-s7QlSlWK38WemQA/view)
- [Interfaces](https://github.com/openAMRobot/openamrobot-interfaces)
- [Contribution rules](https://github.com/openAMRobot/.github/blob/main/CONTRIBUTING.md)
Read relevant sources; if inaccessible, use an approved supplied excerpt and disclose limits.
