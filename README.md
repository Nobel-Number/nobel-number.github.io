# Nobel Index

Your **Nobel number**: the co-authorship distance from any researcher to the nearest Nobel laureate
(Physics, Chemistry, Medicine, Economics), like an Erdős number. 0 is a laureate, 1 co-authored with one, and so on.

- `index.html`, `nobel-number.js`, `data/`: the static website (served at https://nobel-number.github.io). The search runs in the browser against the OpenAlex API, plus a precomputed table of every laureate's co-authors (`data/`).
- `pipeline/`: scripts that build `data/` from the Nobel Prize API and OpenAlex. Order: 01, 04, 04c, 11, 05, 06, 09, 08, 10.
- `tests/smoke.mjs`: runs 52 researchers through the search and re-checks every paper in every chain.

Rules: only peer-reviewed work counts (journal or conference articles, reviews, letters; no preprints, abstracts, errata or retracted papers), and papers with more than 30 authors are ignored.
