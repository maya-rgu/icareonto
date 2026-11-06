# Reviewed catalogue snapshot

`catalogue/current.json` identifies the single complete catalogue release distributed with this package. It contains metadata for 16 approved and complete resources; MAYA-EDU-0014 remains on hold. The catalogue contains source links and annotations, not copies of provider materials.

Use it directly without the source workbook:

```bash
python education/scripts/education_resources.py select --output education/data/catalogue --request education/examples/spanish-cardiovascular.json
```

For curation changes, build into ignored `education/generated/`, test and inspect the change report. Then prepare a fresh publication snapshot and update this directory deliberately. Keep the release folder, pointer, manifest and validation files together because the loader verifies the complete package. Earlier published snapshots remain recoverable through Git history/tags rather than accumulating every local build here.
