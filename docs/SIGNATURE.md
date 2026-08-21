# Signature du code Windows et SmartScreen

## Etat actuel (v1.5.0)

L'installeur Windows n'est pas signé : au premier lancement, Windows affiche
l'avertissement SmartScreen « Windows a protégé votre PC ». L'installation
reste possible via **Plus d'infos → Exécuter quand même**.

## Voie gratuite n°1 : winget (en cours)

Une demande d'ajout au catalogue winget est soumise :
https://github.com/microsoft/winget-pkgs/pull/422097

Une fois fusionnée par Microsoft :

```
winget install GestionScolaire
```

installe l'application **sans alerte SmartScreen** (winget vérifie lui-même
l'empreinte SHA256 de l'installeur). Les mises à jour futures :
`winget upgrade GestionScolaire`.

## Voie gratuite n°2 : SignPath Foundation (signature définitive)

[SignPath Foundation](https://signpath.org) signe gratuitement les projets
open source (licence OSI requise — le dépôt est sous MIT depuis v1.5.0).
Le certificat Sectigo émis au nom de la Foundation supprime l'avertissement
SmartScreen pour les téléchargements directs.

Pipeline déjà branché dans `build_app.py` et les workflows GitHub Actions :
dès que les secrets `SIGNPATH_API_TOKEN` et
`SIGNPATH_CERTIFICATE_PROFILE_ID` existent sur le dépôt, l'exécutable ET
l'installeur Setup sont signés automatiquement à chaque build.

Seule étape manuelle irréductible : déposer la demande sur
https://signpath.org (URL du dépôt, page de téléchargement, description)
et attendre la revue (quelques jours à quelques semaines).

## Alternative payante (pour référence)

Azure Trusted Signing (~10 $/mois, CA Microsoft) : validation d'identité
limitée aux États-Unis et au Canada à ce jour.

## Vérification des fichiers

Chaque release publie `SHA256SUMS.txt` :

```
sha256sum -c SHA256SUMS.txt
```
