# Interface Python pour Teensy SD

Ce script Python permet de communiquer avec le Teensy et de récupérer les données stockées sur la carte SD, reproduisant les fonctionnalités du code Arduino `sd_card_code.ino`.

## Installation

1. Installer les dépendances :
```bash
pip install -r requirements.txt
```

## Utilisation

### Mode interactif (recommandé)
```bash
python teensy_sd_interface.py
```

### Commandes en ligne
```bash
# Lister tous les fichiers
python teensy_sd_interface.py --list

# Télécharger un fichier spécifique
python teensy_sd_interface.py --get data_1234567890.bin

# Spécifier un port série
python teensy_sd_interface.py --port /dev/ttyACM0

# Spécifier un répertoire de sortie
python teensy_sd_interface.py --get data_1234567890.bin --output-dir ./mes_donnees
```

### Utilisation programmatique

```python
from teensy_sd_interface import TeensySDInterface

# Créer l'interface
interface = TeensySDInterface()

# Se connecter
if interface.connect():
    # Lister les fichiers
    files = interface.list_files()
    print("Fichiers disponibles:", files)

    # Télécharger un fichier
    interface.get_file("data_1234567890.bin", "downloaded_files/")

    # Fermer la connexion
    interface.disconnect()
```

## Commandes disponibles

- `list` : Liste tous les fichiers sur la carte SD
- `get <filename>` : Télécharge un fichier spécifique
- `help` : Affiche l'aide des commandes
- `quit` : Quitte le mode interactif

## Fonctionnalités

- **Auto-détection du port** : Le script essaie de trouver automatiquement le port du Teensy
- **Gestion des erreurs** : Gestion robuste des erreurs de communication
- **Sauvegarde automatique** : Les fichiers téléchargés sont sauvegardés dans un répertoire spécifié
- **Interface en ligne de commande** : Support des arguments pour l'automatisation
- **Mode interactif** : Interface conviviale pour l'utilisation manuelle

## Structure des fichiers téléchargés

Les fichiers `.bin` contiennent les données brutes des capteurs avec :
- 5 canaux de données (pins 15, 17, 19, 21, 23)
- Timestamps pour chaque échantillon
- Données pré-trigger et post-trigger
- Format binaire pour un traitement efficace

## Dépannage

1. **Port non trouvé** : Vérifiez que le Teensy est connecté et que les drivers sont installés
2. **Timeout de communication** : Augmentez le timeout dans le code si nécessaire
3. **Fichier corrompu** : Vérifiez la connexion série et réessayez le téléchargement
