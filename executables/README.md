# Exécutables Gestion Scolaire

Livraison **1.6.0** — produite le 09/09/2026 (IA Charo + interface « nombre d'or »).

## Linux (construits localement, smoke-test 12 s OK)

| Fichier | Type | Usage |
|---|---|---|
| `GestionScolaire-1.6.0.AppImage` | Portable (clic) | Ne rien installer : `chmod +x` puis double-clic, ou `./GestionScolaire-1.6.0.AppImage`. |
| `gestion-scolaire_1.6.0_amd64.deb` | Paquet Debian/Ubuntu | `sudo dpkg -i gestion-scolaire_1.6.0_amd64.deb` (ou `sudo apt install ./...`). Lancement via le menu « Gestion Scolaire ». |
| `GestionScolaire-1.6.0-Linux-Portable.tar.gz` | Dossier brut | `tar -xzf ...` puis `./gestion-scolaire/gestion-scolaire`. |

## Windows (via GitHub Actions, job `windows`)

L'exécutable `GestionScolaire.exe` + l'installeur **Inno Setup** et le zip
portable ne peuvent pas être compilés depuis Linux (PyInstaller ne compile
pas en cross-platform). Ils sont produits automatiquement par le tag
**`v1.6.0`** poussé sur GitHub : la Release **Gestion Scolaire 1.6.0**
contient l'installeur `GestionScolaire-Setup-1.6.0.exe`, le zip portable
et les livrables Linux :

https://github.com/laudesmassamba1-ai/Logiciel-de-gestion-scolaire/releases

## Notes

- Builds issus de `build_linux.spec` / `build_win.spec` (PyInstaller,
  Python 3.12) et des recettes `_build_deb()` / AppImage de `build_app.py`
  et `.github/workflows/build.yml`.
- Smoke-test en offscreen (exit 124 après 12 s = application vivante).
- L'appli stocke ses données là où elle tourne (voir `docs/`).