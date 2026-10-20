# sfd2ufo-corrected

Convert FontForge `.sfd` files and `.sfdir` directories to editable **UFO3**, without running FontForge.

```sh
pip install git+https://github.com/david-buck/sfd2ufo-corrected
sfd2ufo-corrected Font.sfdir Font.ufo
```

A small wrapper around [sfdLib](https://github.com/MFEK/sfdLib.py). Its `2.0.0.post0` contour conversion writes implied quadratic endpoints as extra off-curve controls, distorting some curves while leaving widths and bounds unchanged. This replaces that step and converts each quadratic to its mathematically equivalent cubic, without curve fitting or simplification. Existing output files are refused.

Built to recover Roadgeek sources: local checks compared 3,604 segments with the source geometry, plus widths, character mappings, components and kerning. Metadata and OpenType features still depend on sfdLib; this is a focused outline correction, not a complete FontForge replacement. Editable point topology changes when quadratics become cubics.

```sh
python -m unittest discover -s tests -v
```

BSD-3-Clause. See `THIRD_PARTY.md` for upstream attribution.
