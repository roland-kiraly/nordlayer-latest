## Cursor Cloud specific instructions

This is an Arch Linux AUR packaging repo for NordLayer VPN. It contains:

- `PKGBUILD` / `.SRCINFO` / `nordlayer.install` — Arch Linux package build recipe and install hooks
- `update_pkgbuild.py` — Python 3 script that checks for new NordLayer releases, downloads the `.deb`, computes SHA-512, and updates `PKGBUILD` / `.SRCINFO`

### Running the Python update script

```
python3 update_pkgbuild.py
```

The script's `update_srcinfo()` step calls `makepkg --printsrcinfo`, which is only available on Arch Linux. On Ubuntu-based cloud VMs this step will fail with `FileNotFoundError`. All other steps (version check, PKGBUILD update, `.deb` download, checksum) work fine.

The `get_latest_version()` function scrapes HTML from `https://help.nordlayer.com/docs/linux` and can return `None` if the page structure changes or under rate-limiting. A reliable alternative for version checks is:

```
curl https://downloads.nordlayer.com/linux/latest/version
```

### Lint checks

- **Shell scripts**: `bash -n PKGBUILD && bash -n nordlayer.install` for syntax; `shellcheck nordlayer.install` for style (SC2148 about missing shebang is expected — `.install` files are sourced by `makepkg`). Shellcheck warnings on `PKGBUILD` about "unused" variables are false positives (variables are consumed by `makepkg`).
- **Python**: `python3 -c "import py_compile; py_compile.compile('update_pkgbuild.py', doraise=True)"`

### Dependencies

Python 3 with `requests` and `beautifulsoup4` (installed via `pip3 install requests beautifulsoup4`).
