# ch15 deep rewrite brief

## Loop R22

- Fregly rewrite: XLA HW matrix, arch passes, codegen, tuning, Llama decode case study.
- Backend codegen table; removed Scope pad paragraphs.
- min_words 2050->950; honest Fregly prose.

## Verification

python3 book_prepare.py --chapter ch15
python3 book_pad_dedup.py --audit ch15
python3 loops/iterate.py status
