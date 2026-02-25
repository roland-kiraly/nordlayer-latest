## Cursor Cloud specific instructions

This is an Arch Linux AUR packaging repo for NordLayer VPN. It contains:

- `PKGBUILD` / `.SRCINFO` / `nordlayer.install` — Arch Linux package build recipe and install hooks
- `update_pkgbuild.py` — Python 3 script that checks for new NordLayer releases, downloads the `.deb`, computes SHA-512, and updates `PKGBUILD` / `.SRCINFO`

### Running the Python update script

```
python3 update_pkgbuild.py
```

The script runs fully on Ubuntu-based cloud VMs (`.SRCINFO` is generated in Python, no `makepkg` needed).

Version detection tries three sources in order: **Debian Packages index** (most reliable), HTML scraping, then the `/linux/latest/version` API. Every candidate is validated with a HEAD request to the `.deb` URL before being accepted. The version API is known to be stale (currently returns 3.3.2 whose `.deb` is 404), so the Packages index is the authoritative source.

### Lint checks

- **Shell scripts**: `bash -n PKGBUILD && bash -n nordlayer.install` for syntax; `shellcheck nordlayer.install` for style (SC2148 about missing shebang is expected — `.install` files are sourced by `makepkg`). Shellcheck warnings on `PKGBUILD` about "unused" variables are false positives (variables are consumed by `makepkg`).
- **Python**: `python3 -c "import py_compile; py_compile.compile('update_pkgbuild.py', doraise=True)"`

### Dependencies

Python 3 with `requests` and `beautifulsoup4` (installed via `pip3 install requests beautifulsoup4`).
