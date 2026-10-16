# GitHub readiness (checked; nothing has been published)

- Files needed to run: all present (`index.html`, `style.css`, `pyscript.toml`, 15 `.py` files). Every module is listed in `pyscript.toml`.
- Secrets: none found. `auth.py` only generates random password salts (`secrets.token_hex`). The project uses no API keys, tokens, or `.env` files.
- Generated files: none in the project. `.gitignore` added for `__pycache__`, editor files and `.env`.
- Works on GitHub Pages as a static site (Settings -> Pages -> main branch). Needs internet for PyScript, Lucide, qrcode-generator and Google Fonts.
- Missing before a public release: the promotional video (`assets/`), a LICENSE (the group must choose), group member names and contributions in the README, and an up-to-date README (see `docs/README_OUTLINE.md`).
- Please confirm the contact email and opening hours in `data.py` are real before publishing.
