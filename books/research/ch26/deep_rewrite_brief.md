# ch26 deep rewrite brief

## Loop R20

- Fregly rewrite: env packaging, multi-HW ops, pitfalls, heterogeneous scheduling.
- Packaging layers table; bridges ch22–25 and Part VIII.
- `iterate.py`: pad dedup tasks now recommend deep-rewrite when strip would leave <1000 words.

## Verification

```bash
python3 book_prepare.py --chapter ch26
python3 book_pad_dedup.py --audit ch26
```
