# 02 · Parquet: layout before tuning

## Goal and prerequisites

Complete 01. Know rows, columns and integer predicates. Explain a Row Group, inspect encodings and compression, then measure what a reader actually requests.

## A vertical slice within a horizontal slice

A Row Group contains a set of rows. Within it, each leaf column has a column chunk, divided into pages. A dictionary substitutes repeated values with codes; run-length encoding represents repeated runs; compression transforms encoded page bytes. These are separate decisions. A low-cardinality label column can benefit from a dictionary even when the random payload column does not.

The footer lets a reader locate chunks without decoding every row. Suppose a group has integer id bounds [0,4095]. The inclusive predicate [32000,33023] cannot match it. A group with [0,131071] cannot be excluded by those bounds even if it happens to contain no matching row. Bounds supply a safe rejection test, not an answer to the query.

Sorting narrows min/max intervals along the sorted key. Smaller groups offer finer rejection but increase metadata and scheduling work. Larger groups may improve sequential reading and compression while retaining more irrelevant rows. There is no universally optimal group size.

## Data and executable code

`experiments/parquet_layout.py` generates 131,072 rows using seed 9162026. Schema: integer id/value, 32 bucket labels and a deterministic SHA256 text payload. Five files vary sorted/shuffled order, 4,096/32,768 target rows per group and ZSTD/Snappy. Only bucket uses dictionary encoding. Every file is fully decoded, sorted by id and compared against the same logical table before queries begin.

```sh
python lab.py parquet
python scripts/inspect_parquet.py build/parquet/sorted-4096-zstd.parquet
```

The three modes return the same ordered id/value rows: wide read with pushed filter; projected read with pushed filter; projected read without pushdown followed by exact filtering. The last is a control for reading all groups. One warm-up and three alternating-order measured repetitions are kept for every mode.

## Actual results and interpretation

Open the evidence page for all 45 recorded runs. For the saved 4,096-row ZSTD files, sorted order retains 2 of 32 candidate groups; shuffled order retains all 32. The exact result has 1,024 rows. Projection also removes payload requests. The report separates estimated candidate compressed chunk bytes from counted engine read requests. Metadata reads can overlap; filesystem cache hits still count as requests. These are not physical disk or network counters.

Elapsed times include read, decode, exact filtering and result sorting, excluding file creation and validation. They are warm-cache laptop observations. A lower requested byte count need not produce a faster tiny query; overhead and cache matter.

## Hands-on task

Change the predicate to fit inside one sorted group, then straddle a boundary. Predict candidate counts before running. Change the sort key to bucket: does it still help an id predicate? Use the browser inspector with a synthetic file, choose a column and compare the min/max strips. Its estimates never claim that an SQL engine executed the query.

## Self-check

**Can a projected query still read the filter column?** Yes; a predicate needs its values unless metadata resolves it. **Does compression remove the need for pruning?** No; skipping a chunk and decompressing it solve different costs. **Can missing statistics prove rejection?** No. Keep the group as a candidate.

## Guided university reading and original exercise

- [Carnegie Mellon University 15-445/645 · Fall 2025 · Lecture #06 · Storage Models & Compression](https://15445.courses.cs.cmu.edu/fall2025/slides/06-storage3.pdf)
- [Massachusetts Institute of Technology 6.5830/6.5831 · Spring 2026 · Lecture 10 / 2026-03-10 · OLAP & Column Stores](https://dsg.csail.mit.edu/6.5830/lectures/lec10.pdf)
- [Apache Parquet · File metadata and page headers · Parquet metadata](https://parquet.apache.org/docs/file-format/metadata/)

Predict candidate groups before comparing real read spans; change one predicate boundary in your own copy.

```sh
python lab.py parquet
```

All 45 queries return the same source-oracle rows; sorted 4096 layout retains 2/32 candidates while shuffled retains 32/32.

These are original Lab exercises, not the universities’ assignment solutions. Public reading access does not grant enrollment, credit or grading. See the searchable resource library for prerequisites and verification dates.

## Original sources

- [Parquet column chunks](https://parquet.apache.org/docs/file-format/data-pages/columnchunks/)
- [Parquet encodings](https://parquet.apache.org/docs/file-format/data-pages/encodings/)
- [Parquet metadata](https://parquet.apache.org/docs/file-format/metadata/)
- [PyArrow Parquet reader API](https://arrow.apache.org/docs/20.0/python/generated/pyarrow.parquet.read_table.html)
