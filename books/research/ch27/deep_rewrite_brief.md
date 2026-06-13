# ch27 deep rewrite brief

## Loop R21

- Fregly rewrite: co-design, new architectures, edge–cloud, autonomous kernels.
- Trend→counter→gate table; bridges Part VII and Part VIII (ch28–30).
- `min_words` 1650→950; 1672→985 words after pad removal.

## Verification

```bash
python3 book_prepare.py --chapter ch27
python3 book_pad_dedup.py --audit ch27
python3 book_spec_audit.py
```
