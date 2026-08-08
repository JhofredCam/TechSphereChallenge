# Agent Instructions

## Repository Shape

- This checkout is the implementation fork of the Tech Sphere Challenge 2026 starter/data repository. Add the application, toolchain, tests, and executable documentation here; at this baseline there is no package manifest, lockfile, build/lint/typecheck/test configuration, CI workflow, or app entrypoint, so do not assume a package-manager command exists.
- Read `README.md` for the product contract, `docs/rubrica-evaluacion.md` for elimination gates and required metrics, and `docs/stack-tecnico.md` for the closed list of allowed language-model families.
- Document and verify the fork's real setup, run, and focused-test commands in the README; prefer the implementation's scripts/config files over stale prose.

## Dataset Traps

- All challenge inputs are already local under `dataset/`; they are synthetic and not clinically validated. Do not add an external data-download prerequisite.
- Each XLSX has one sheet named `result`; `comorbilidades` and `adaptation_fields` are JSON strings inside cells.
- `dataset/dataset_final.xlsx` is turn-level, not call-level. Filter `capa1_limpia` or `capa2_ruidosa` before rebuilding a conversation; layer-2 derived turns use `_c2` and inserted third-party turns use `_c2_tercero`.
- `paciente_id` links the four spreadsheets. The conversation-to-trajectory join is `caso_id = "caso_" + trayectoria_id`; one `caso_id` intentionally has both conversation layers.
- Ingest `dataset/textos/` recursively and handle paths with spaces, duplicate PDFs, and the scanned PDF in `Appendicitis/` that has no text layer; do not assume every PDF yields text directly.

## Challenge Constraints

- An implementation must expose both surfaces: an admin console to upload, list, and delete knowledge documents with visible processed/available status, and a browser/API voice call interface with microphone input and agent audio.
- The call is browser/API-based, not real telephony, and the agent speaks Spanish for Colombian patients. Clinical answers must be grounded in the corpus, traceable to sources, and able to learn from an upload and forget a deleted document.
- Only the model families listed in `docs/stack-tecnico.md` are allowed; orchestration, voice, RAG, and embeddings are otherwise open. Declare the exact model/version and rationale in the final report.
- The documented setup must be runnable in 15 minutes or less. Real-time voice and live knowledge upload/delete are elimination gates, so verify both rather than relying on mocks.

## Commit Policy

- When a requested task is complete, always create a Git commit before finishing the session.
- Inspect `git status`, the relevant diff, and recent history before committing.
- Stage only files changed for the current task; never include unrelated user or generated changes.
- Do not commit secrets, local runtime data, credentials, or agent-specific configuration.
- After the commit, always push the current branch to its configured remote before finishing.

## Branch Policy

- Every new specification must be developed on its own dedicated branch, created before editing.
- Use the naming convention `spec/<short-slug>`; for example, `spec/testing-unit-integration`.
- Do not combine two independent specs in one branch or implement a new spec directly on `main`.
- The spec branch must be pushed after its commit, unless the user explicitly asks not to push.
