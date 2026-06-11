# Vendor dependencies (`deps/`)

Git **submodules** (shallow, `--depth 1`) for compiler/runtime upstream trees referenced in Part VI–VIII. Book prose cites papers and APIs; **source of truth for Pass names, directory layout, and build** is these trees.

## Submodule map

| Path | Upstream | Book chapter | Notes |
|------|----------|--------------|--------|
| [`YiRage/`](YiRage/) | [chenxingqiang/YiRage](https://github.com/chenxingqiang/YiRage) | ch20, ch25, **ch29–30** | LLM inference compiler + PK runtime |
| [`llvm-project/`](llvm-project/) | [llvm/llvm-project](https://github.com/llvm/llvm-project) | **ch14** (MLIR) | MLIR → `llvm-project/mlir/` |
| [`xla/`](xla/) | [openxla/xla](https://github.com/openxla/xla) | **ch15** | OpenXLA / XLA compiler |
| [`tvm/`](tvm/) | [apache/tvm](https://github.com/apache/tvm) | **ch16** | Apache TVM stack |
| [`triton/`](triton/) | [triton-lang/triton](https://github.com/triton-lang/triton) | **ch17** | Triton GPU kernel language |
| [`iree/`](iree/) | [iree-org/iree](https://github.com/iree-org/iree) | **ch18** | MLIR-native runtime + compiler |
| [`glow/`](glow/) | [pytorch/glow](https://github.com/pytorch/glow) | **ch19** | Glow (legacy CPU/edge compiler) |

## Clone / update

From repo root:

```bash
# All book deps (recommended after clone)
git submodule update --init --depth 1 deps/

# Or one at a time
git submodule update --init --depth 1 deps/llvm-project deps/xla deps/tvm deps/triton deps/iree deps/glow deps/YiRage

# YiRage has nested submodules
git submodule update --init --recursive deps/YiRage
```

Fresh clone:

```bash
git clone --recurse-submodules --depth 1 https://github.com/chenxingqiang/auto-loops-books.git
# then: git submodule update --init --recursive deps/YiRage
```

## Size / scope

- **`llvm-project`** is large even with `--depth 1`; init only when editing ch14/MLIR or tracing YiRage MLIR paths.
- Other compiler submodules are smaller; safe to init for ch15–ch19 agent tasks.
- Do **not** hand-edit vendor trees in this repo—patch upstream or pin submodule SHAs in commits.

## YiRage build (Part VIII)

See [`YiRage/docs/INSTALLATION.md`](YiRage/docs/INSTALLATION.md):

```bash
cd deps/YiRage
YIRAGE_BACKEND=cpu pip install -e .
python -c "import yirage as yr; print(yr.get_available_backends())"
```

## Quick paths for agents

| Topic | Start here |
|-------|------------|
| MLIR dialects / passes | `deps/llvm-project/mlir/` |
| XLA HLO / fusion | `deps/xla/xla/` |
| TVM tuning / TIR | `deps/tvm/python/tvm/`, `deps/tvm/src/` |
| Triton kernels | `deps/triton/python/triton/` |
| IREE flow / VMVX / HAL | `deps/iree/compiler/`, `deps/iree/runtime/` |
| Glow graph lowering | `deps/glow/lib/` |
