# ch22 deep rewrite brief

## Machine pass (Loop R18)

- Fregly rewrite: profiling / bottleneck / workflow / regression gates.
- Removed pad tail (12 Scope blocks → 0); updated figure captions + profiling table.
- `pad_restart_index`: case-insensitive hooks + Scope-count detection.

## Verification

```bash
python3 book_prepare.py --chapter ch22
python3 book_pad_dedup.py --audit ch22
```
