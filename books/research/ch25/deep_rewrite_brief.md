# ch25 deep rewrite brief

## Machine pass (done by `book-loop deep-rewrite`)

- Stripped pad-duplicate tail; replaced template section bodies with Fregly prose.
- Added RL search axes table; updated figure captions for RL loop and reward pipeline.
- Target: decode-aware autotune (RL + hardware reward + YiRage fingerprints).

## Agent follow-ups (optional)

- Stretch to 3500+ words with Part VI backend-specific case studies (XLA vs TVM trials).
- Add second table: reward weight presets per SKU tier.
- Cross-link ch21 benchmark harness with concrete command examples.

## Verification

```bash
python3 book_prepare.py --chapter ch25
python3 book_spec_audit.py
```
