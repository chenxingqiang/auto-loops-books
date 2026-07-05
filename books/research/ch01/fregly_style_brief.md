# ch01 Fregly/O'Reilly style alignment (2026-07-04)

Restructured `ch01_llm_decode_bottlenecks.tex` per style gap analysis:

- **Opening hook**: DeepSeek fleet ratio + composite production postmortem narrative
- **Engineering logic**: industrial_hook → prefill/decode → three pain points → frameworks → goodput → diagnosis → multi-HW → baselines → YiRage → roadmap → profiling → takeaways → conclusion
- **Goodput**: unified four-counter table with business mapping
- **Visuals**: roofline (distinct prefill/decode points), kernels/token bar chart, baseline ladder (replaced pending fig)
- **Tone**: practice notes, anti-patterns, engineer-to-engineer voice
- **Key Takeaways**: Fregly-style bold title + multi-sentence paragraphs
- **OUTLINE**: `book_prepare.py` ch01 section patterns updated

## Verify
python3 book_prepare.py --chapter ch01
