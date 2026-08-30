# Data Attribution

This repository includes a subset of judgments from the **Indian Supreme Court
Judgments** dataset, a public dataset distributed through the **Registry of
Open Data on AWS** and licensed under **CC-BY-4.0**.

## Source

- **Dataset:** Indian Supreme Court Judgments
- **Registry:** https://registry.opendata.aws/indian-supreme-court-judgments
- **Maintainer:** Dattam Labs (https://dattam.in); contact@dattam.in
- **License:** CC-BY-4.0
- **Coverage:** Supreme Court of India judgments, 1950–2025, sourced from the
  eCourts website; English and regional Indian languages.
- **S3:** `arn:aws:s3:::indian-supreme-court-judgments` (region `ap-south-1`)
- **Documentation:** https://github.com/vanga/indian-supreme-court-judgments/blob/main/opendata/docs/dataset.md

## How Kautilya uses it

Kautilya selects a small landmark-judgment corpus from this dataset and chunks it
into the `SCJ` index collection (see `scripts/fetch_scj.py`, which resolves the
landmark manifest against the public S3 metadata index, and
`scripts/build_scj_chunks.py`). Only a curated subset of judgments is used; the
full dataset is not vendored into the repository.

## Citation

Per the Registry's citation guidance:

> Indian Supreme Court Judgments was accessed on 2026-08-30 from
> https://registry.opendata.aws/indian-supreme-court-judgments.

Indices are refreshed from the source periodically; consult the linked
documentation for the most recent update cycle.
