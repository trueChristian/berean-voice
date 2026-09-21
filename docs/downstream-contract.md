# Downstream content contract

## Ownership

This repository remains the authoritative English archive extracted from the printed Berean Voice issues. The separate website repository assembles and deploys the site. A separate translation repository owns translation, terminology review, and approval. Website templates, generated pages, and translated article bodies do not belong here.

The archive's files and metadata will be deliberately aligned for a downstream static build, including GitHub Pages. This structural migration must not change original article wording, meaningful HTML structure, article UUIDs, image pixels, source credits, rights decisions, or verification claims.

## Migration in this pull request

All work uses one branch and one pull request, with separately reviewable commits:

1. Establish the repository boundary and migration acceptance criteria.
2. Define and implement a versioned content layout and stable catalogue identities.
3. Migrate existing article/image paths and normalize navigational references without silently changing source labels.
4. Update the canonical AGENTS.md ingestion instructions and README for future issues.
5. Add deterministic validation, derived navigation, source fingerprints, and a display-only export for the website.
6. Verify the migrated archive against the original revision and test root-domain and GitHub Pages project-base output paths.

## Acceptance criteria

- Every original article UUID is retained exactly once.
- Every article's source wording and semantic structure are preserved; only documented asset URL transformations are permitted.
- Image bytes, captions, credits, issue provenance, skipped records, and source verification claims remain unchanged.
- All indexed files exist, all exported files are indexed, and every local article image reference resolves to its owning article's asset.
- Categories, topics, series, and issues have stable IDs; article references resolve to the canonical registry.
- Ambiguous grouping decisions are explicit and reviewable. Original source labels are retained rather than silently rewritten.
- Navigation and fingerprints are deterministic derived data, not a second editable source of truth.
- A downstream export includes display-related content only, records its source revision, and supports both a root URL and a project-site base path.
- Failed validation blocks export. This repository does not deploy a website or publish unapproved translations.
- Future ingestion follows the same checked contract and does not recreate the old layout.

The final layout, commands, schema and verification results will be documented here as the implementation is committed. This initial commit establishes the review boundary; it does not claim that the migration has already run.
