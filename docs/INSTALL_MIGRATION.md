# Install Source Migration

The installer has been updated to install this fork and GUI branch instead of the upstream/original repository.

## One-liner

```bash
curl -sSL https://raw.githubusercontent.com/dcooper94/hackingtool/hacktool-gui-v2/install.sh | sudo bash
```

## What changed

- `install.sh` now clones `https://github.com/dcooper94/hackingtool.git`.
- `install.sh` now pins branch `hacktool-gui-v2`.
- `install.py` now clones the same branch when installing from GitHub.
- `update.sh` now resets the install origin to this fork and branch before updating.
- README installation instructions now point to this fork/branch.

## Existing GUI installs

If your current install was created using the old one-liner, `/usr/share/hackingtool` is likely a clone of `https://github.com/Z4nzu/hackingtool.git`, and `/usr/bin/hackingtool-gui` launches that old checkout. It will not see the reviewed changes until you migrate or reinstall.

Preferred migration:

```bash
curl -sSL https://raw.githubusercontent.com/dcooper94/hackingtool/hacktool-gui-v2/install.sh | sudo bash
```

Manual migration:

```bash
sudo git -C /usr/share/hackingtool remote set-url origin https://github.com/dcooper94/hackingtool.git
sudo git -C /usr/share/hackingtool fetch --depth 1 origin hacktool-gui-v2
sudo git -C /usr/share/hackingtool checkout -B hacktool-gui-v2 origin/hacktool-gui-v2
sudo /usr/share/hackingtool/venv/bin/pip install --quiet --upgrade -r /usr/share/hackingtool/requirements.txt
```

User data under `~/.hackingtool` is separate from `/usr/share/hackingtool` and should be preserved by a normal reinstall or source replacement.
