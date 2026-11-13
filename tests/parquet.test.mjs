import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  inspectParquet,
  candidateGroups,
  decodeFooter,
} from "../site/parquet.mjs";
const report = JSON.parse(
  fs.readFileSync(new URL("../results/parquet.json", import.meta.url)),
);
for (const name of ["sorted-4096-zstd", "shuffled-4096-zstd"])
  test("real generated footer matches PyArrow: " + name, async () => {
    const data = fs.readFileSync(
      new URL("../build/parquet/" + name + ".parquet", import.meta.url),
    );
    const blob = new Blob([data]);
    const parsed = await inspectParquet(blob);
    const expected = report.variants.find((x) => x.name === name).metadata;
    assert.equal(parsed.rows, String(expected.rows));
    assert.equal(parsed.row_groups.length, expected.row_groups.length);
    for (let i = 0; i < parsed.row_groups.length; i++)
      for (let j = 0; j < 4; j++) {
        const a = parsed.row_groups[i].columns[j],
          b = expected.row_groups[i].columns[j];
        assert.equal(a.path, b.path);
        assert.equal(a.codec, b.codec);
        assert.equal(a.compressed_bytes, b.compressed_bytes);
        assert.equal(String(a.min), String(b.min));
        assert.equal(String(a.max), String(b.max));
      }
    assert.equal(
      candidateGroups(parsed, "id", 32000, 33023).filter((x) => x.candidate)
        .length,
      expected.candidate_groups,
    );
  });
test("reject invalid/truncated/encrypted footer", async () => {
  await assert.rejects(() => inspectParquet(new Blob(["PAR1badPAR1"])));
  assert.throws(() => decodeFooter(new Uint8Array([0x19, 0xff]), 12));
  await assert.rejects(() =>
    inspectParquet(new Blob(["PAREsomeencryptedfooterPARE"])),
  );
});
test("unknown statistics stay candidates and unsafe bounds reject", () => {
  const p = {
    row_groups: [
      {
        index: 0,
        columns: [{ path: "id", physical_type: "INT64", min: null, max: null }],
      },
    ],
  };
  assert.equal(candidateGroups(p, "id", 1, 2)[0].candidate, true);
  assert.throws(() => candidateGroups(p, "id", 3, 2));
  assert.throws(() => candidateGroups(p, "id", 0, Number.MAX_SAFE_INTEGER + 1));
});
