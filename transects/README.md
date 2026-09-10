# AFP4 transect builder

This isolated builder replaces the twelve frozen A–F `s2*_mr.html` and
`s2*_max.html` applications with maintainable static pages. It does not modify
any Private GIS, Public GIS, Storymap, server, authentication, or main-map data.

**Production publication authorized for client review on September 9, 2026.**
The user explicitly requested deployment to the existing production pages after
being advised that coordinate authority remains unresolved. The deployed build
is `build/production-20260909T1604Z-v2/`, built with `--production-review`.
It retains the position-comparison control and per-well position checks, and does not
represent geometry as approved (`geometryApproved: false`). The default builder
still creates a local-only preview; do not deploy that preview as-is.

September 10 presentation update: build with `--production-review
--hide-review-banners` to hide only the two yellow banner messages, as explicitly
requested. This does not change the source data, marker coordinates, history,
comparison control, per-well position checks, or unresolved geometry status.
See `releases/2026-09-10.md`; the current build is
`build/production-20260910T0021Z/`.

The user subsequently authorized merging the four existing PRs and aligning
`main` with production. See `../ops/releases/2026-09-10-main-sync.md` for the full
application-build comparison and tracked nginx configuration. Merge approval
does not resolve the remaining GIS questions or change this builder's default
local-preview behavior.

## Inputs and repeatable build

Requires Python 3.10+; the shipped viewer has no third-party JavaScript runtime
dependencies. Node 18+ runs the display-rule tests. No Docker, GIS installation,
database access, or modification of the source archives is needed for the build.

Run from `Scripts-Files`:

```sh
python3 transects/build.py \
  --transects '/path/to/Transects_NAD83.zip' \
  --aa '/path/to/Transect_A_A.zip' \
  --output transects/build/new-review

python3 -m unittest discover -s transects -p 'test_*.py' -v
node --test transects/test_model.mjs

python3 transects/verify_build.py \
  --build transects/build/new-review \
  --transects '/path/to/Transects_NAD83.zip' \
  --aa '/path/to/Transect_A_A.zip'
node transects/verify_model.mjs transects/build/new-review

python3 -m http.server 8765 --bind 127.0.0.1 \
  --directory transects/build/new-review
```

Open `http://127.0.0.1:8765/review.html`. The output must be a **new** directory;
the builder refuses to overwrite a previous release or an application. B–F are
read from the first ZIP; its old A–A files are explicitly ignored. Both A–A
variants must come from the complete replacement ZIP.

## Data rules

- Validate ZIP integrity, DBF schema/counts, every SHP/SHX record boundary,
  projection sidecars, fields, dates, values, and profile geometry.
- Require all three analytes, groundwater records, the expected section, and
  source perpendicular distances below 20 feet. Do not impose extra date filters.
- Require MR/MAX source variants to be byte-identical, as Mary explicitly
  described. If that contract changes, stop and review the new source semantics.
- Collapse repeated `(well, analyte, date, result)` keys for plotting, keeping
  **every contributing DBF row number** as provenance. This is display
  deduplication, not a claim that independently identified lab samples are the
  same physical sample. Original ZIPs and hashes remain the source of truth.
- Most Recent retains all distinct results on the latest available date.
  Maximum retains every date tied for the largest value. No averaging,
  latest-date fabrication, or arbitrary result selection is performed.
- Preserve zero as numeric zero; do not invent a nondetect flag or treat a missing
  result as zero. These profile exports have no separate `Units` or `Lab_Flag`
  columns. The viewer retains the existing µg/L display convention for the
  supplied `*_ppb_l` analytes; it performs no concentration conversion.
- History comes from the same verified section source as the colored screens,
  not an old embedded bundle or an unverified merge from other application data.
- Preserve the published color thresholds and background diagrams. Dates are
  computed from each actual history; no fixed 2020 cutoff remains.

## Geometry review, not an automatic correction

The SHP profiles contain **distance/exaggerated-elevation screen lines**, not
geographic map positions, despite their StatePlane projection declaration.
Do not reproject them as though they were wells on a map.

The original Vue components supply the display calibration, including the 20x
elevation scale. The preview offers two distinct views:

1. **Exported screen geometry**: `X`, `exg_tos_el`, `exg_bos_el`, checked directly
   against SHP vertices.
2. **Joined coordinate fields**: `X_1`, `exg_tos__1`, `exg_bos__1`.

No field is silently substituted for another. Multiple positions are retained;
dashed screens and the table identify cases needing review. Published geological
labels are static reference labels; click a colored screen or table well for its
actual measurement identity and history.

The checked September inputs flag 14 wells with multiple selected-result
positions or coordinate differences. This is not a count of proven errors:
many occur on adjacent subsegments. Examples:

- AA / HM-106: along-section positions 1,976.01 and 2,007.25 feet for the same
  selected measurements and screen elevations.
- BB / EPA-2 (Maximum): three exported screen geometries, but one joined
  coordinate position; some screens also disagree in elevation.
- FF / WJETA087: along-section positions 10,582.49 and 10,605.26 feet.

Mary confirmed that a well may appear on multiple transects and should be shown
relative to the displayed transect. This does not resolve the shape-versus-joined
field discrepancy within the EPA-2 example. Merely choosing
the first row, minimum perpendicular distance, most common geometry, or old
published pixel position is not an approved resolution.

FF / HM-114 also has distinct same-day latest TCE results (310 and 330) and cis
results (38 and 39). Both are preserved in the preview, history, table, and
striped screen. No analytical judgment is made between them.

`validation.json` contains all exceptions, source hashes, section membership
changes, dates, record counts, and exact source row provenance. Additional
geographic checks may support review, but the six navigation-map lines need not
be an identical version of the profile construction lines. A difference alone
does not establish which source is wrong.

## Legacy diagram provenance

`legacy/` freezes the original SVG annotations, unchanged background PNGs,
screen positions, and calibration. `origins.json` records the exact input file
hashes. These are recovered from the repository's published HTML and inline
source maps, not newly interpreted geological diagrams.

`import_legacy.py` performs the one-time import from an original application
`public/` directory into a **new** destination. It is not part of normal data
updates. Do not point it at an already-rebuilt output.

## Production handoff, after source resolution and approval

1. Resolve the position exceptions explicitly, add regression cases, remove the
   review-only coordinate selector/banner, and complete a release review.
2. Rebuild and re-run source reconciliation, tests, and browser checks for all
   six sections × three analytes × two display modes, including well histories.
3. Prepare an allowlisted transect-only change for each application's `public/`
   directory: twelve HTML pages plus `transects-assets/`. Their relative links
   work under `/AFP4/`, `/AFP04/`, and `/storymap/afp4/`.
4. **Do not copy the review directory wholesale.** `review.html`,
   `validation.json`, and `manifest.json` are review artifacts, not replacements
   for the main map shell or its data. Preserve the completed 37-well update.
5. Follow the root `AGENTS.md` and each application README for reviewed builds,
   GitHub authorization, production approval, rollback, and smoke tests. Retain
   old hashed assets for cached shells, and verify HTML revalidation for these
   stable transect page URLs. All new JS, JSON, and PNG asset names are hashed.

For an explicitly authorized production review, `--production-review` changes
only the publication notice/metadata; it does not resolve geometry or select a
different coordinate source. `--hide-review-banners` additionally hides the two
banner messages without changing the underlying position checks. See the release
record before using it. `sync_release.py --build <build> --application <app>`
installs the 27 verified generated files into a clean local application's
`public/` directory, preserving unrelated files and old assets. It performs no
remote operation. Future application builds must retain these source copies.

Nothing in this package sends email, changes access, or replaces the separate
deferred Public performance work.
