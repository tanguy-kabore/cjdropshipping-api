# CJDropshipping API Burkina Faso

## Description
API RESTful pour l'intégration CJDropshipping avec distribution centralisée au Burkina Faso.

Cette API est conçue selon un modèle où toutes les commandes sont livrées à une adresse centrale au Burkina Faso,
permettant ensuite au propriétaire de gérer la distribution aux clients finaux.

## Installation

```bash
pip install -r requirements.txt
```

## Lancement de l'API

```bash
uvicorn main:app --reload
```

## Configuration requise
- Créez un fichier `.env` avec les variables suivantes :
  ```
  # Variables d'authentification (obligatoires)
  CJDROPSHIPPING_API_KEY=votre_clé_api
  CJDROPSHIPPING_EMAIL=votre_email
  
  # Variables pour l'adresse de livraison centralisée (optionnelles, valeurs par défaut fournies)
  SHIPPING_ZIP=10000
  SHIPPING_COUNTRY_CODE=BF
  SHIPPING_COUNTRY=Burkina Faso
  SHIPPING_PROVINCE=Kadiogo
  SHIPPING_CITY=Ouagadougou
  SHIPPING_ADDRESS=votre_adresse_complète
  SHIPPING_CUSTOMER_NAME=votre_nom_complet
  SHIPPING_PHONE=votre_téléphone
  ```

## Documentation API
La documentation complète de l'API est disponible via Swagger à l'URL `/docs` après le démarrage du serveur.

## Fonctionnalités
- Authentification automatique avec CJDropshipping
- Recherche de produits dans le catalogue CJDropshipping
- Création et gestion des commandes
- Calcul des frais d'expédition
- Suivi des colis
- Consultation du solde du compte
