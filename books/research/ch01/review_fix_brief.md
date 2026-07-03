# ch01 review fixes (2026-07-04)

Applied external review feedback:

- Added reader prerequisites paragraph.
- Reordered sections: roofline/memory bandwidth before framework + overhead quant.
- Merged diagnostic workflow into overhead section; roofline intuition into memory section.
- Moved anti-patterns after Key Takeaways; condensed Key Takeaways.
- TaxBreak/LIMINAL/Memory-Floor citations; MMA/ADF expansions; 44ms qualifier.
- Three optimization layers (vLLM vs Flash vs MegaKernel); Flash-Decoding 8x as attention-kernel not E2E.
- Table source footnotes; 10:1 decode:prefill ratio; config labels for 844 vs 847.5.
- Figure fusion_gap caption: pending fill-in noted.
- Reflection question in conclusion.

## Verify
python3 book_prepare.py --chapter ch01
