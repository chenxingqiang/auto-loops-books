# ch23 deep rewrite brief

## Loop R19

- Fregly rewrite: LLM decode compile, MoE scheduling, KV hardware, hetero MoE.
- Removed 12× Scope pad tail; decode invariants table + updated figures.
- Part VI ch15–21 still carry residual pad (audit detects); needs per-chapter rewrite, not batch strip.

## Verification

```bash
python3 book_prepare.py --chapter ch23
python3 book_pad_dedup.py --audit ch23
```
