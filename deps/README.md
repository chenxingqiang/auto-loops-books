# Vendor dependencies (`deps/`)

This directory holds **git submodules** referenced by the book harness and co-design chapters (Part VIII).

## YiRage

| Item | Value |
|------|--------|
| Path | [`YiRage/`](YiRage/) |
| Upstream | https://github.com/chenxingqiang/YiRage |
| Role | Multi-backend LLM inference compiler + **Persistent Kernel runtime** (Layer 5) |

### Clone / update

From repo root:

```bash
git submodule update --init --recursive deps/YiRage
cd deps/YiRage && git submodule update --init --recursive   # YiRage's own deps/
```

Fresh clone of **auto-loops-books**:

```bash
git clone --recursive https://github.com/chenxingqiang/auto-loops-books.git
```

### Build (for agent verification)

See [`deps/YiRage/docs/INSTALLATION.md`](YiRage/docs/INSTALLATION.md). Typical editable install:

```bash
cd deps/YiRage
YIRAGE_BACKEND=cpu pip install -e .    # or cuda / mps / ascend per SKU
python -c "import yirage as yr; print(yr.get_available_backends())"
```

Book chapters **ch29–ch30** map to YiRage's five-layer stack (Python API → Backend Manager → Search → Threadblock ops → **PK runtime**). Source of truth for APIs: submodule tree, not prose alone.
