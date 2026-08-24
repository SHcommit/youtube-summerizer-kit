# Benchmark Reference Drafts

These Markdown files are an AI-assisted review queue, not executable benchmark
references. They are based on anonymously retrieved public captions and must
not be passed to `chew benchmark run --reference`.

For each candidate, a human reviewer must replay the linked source at the
timestamp, check the caption wording and surrounding context, then mark the
candidate `approve`, `revise`, or `reject`. Only approved candidates may be
transcribed into a separate JSON reference that passes the structural checks
documented in `benchmarks/README.md`.

Do not add model-generated claims directly to a live reference. Do not change
the source URL, language, or duration metadata while reviewing.
