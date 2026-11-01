# external/

`external/impossiblebench/` holds upstream [ImpossibleBench](https://github.com/safety-research/impossiblebench) as a git submodule, pinned at commit `061dc3d` (2025-12-01). It is never edited; all of this project's changes wrap upstream functions from `src/hawthorne/`.

After cloning this repository:

```bash
git submodule update --init --recursive
```

If you are rebuilding this repository from a plain copy (no `.git` yet), add the submodule once:

```bash
git submodule add https://github.com/safety-research/impossiblebench external/impossiblebench
git -C external/impossiblebench checkout 061dc3dce6a96ab6cf02a855157263033dcfa3ba
```
