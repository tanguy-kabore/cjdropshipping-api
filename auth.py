"""
Script d'authentification pour l'API CJDropshipping
Permet d'obtenir un token d'accès à partir des identifiants
"""
import requests
import os
import json
from dotenv import load_dotenv

def get_access_token(email=None, password=None):
    """
    Obtient un token d'accès en utilisant les identifiants CJDropshipping
    
    Args:
        email (str): Email du compte CJDropshipping
        password (str): Mot de passe ou clé API du compte
        
    Returns:
        dict: Informations du token ou None en cas d'erreur
    """
    # Charger les identifiants depuis .env si non fournis
    load_dotenv()
    email = email or os.getenv('CJDROPSHIPPING_EMAIL')
    password = password or os.getenv('CJDROPSHIPPING_API_KEY')
    
    if not email or not password:
        print("Erreur: Email ou mot de passe/clé API non fournis")
        return None
    
    # URL d'authentification selon la documentation
    auth_url = "https://developers.cjdropshipping.com/api2.0/v1/authentication/getAccessToken"
    
    # Préparer les données
    payload = {
        "email": email,
        "password": password
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # Effectuer la requête
        response = requests.post(auth_url, headers=headers, json=payload)
        print(f"Statut de la réponse: {response.status_code}")
        
        # Traiter la réponse
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 200:
                print("Authentification réussie!")
                # Stocker le token dans un fichier pour utilisation ultérieure
                with open(".token", "w") as token_file:
                    json.dump(data.get('data'), token_file)
                return data.get('data')
            else:
                print(f"Erreur d'API: {data.get('message')}")
                print(f"Code d'erreur: {data.get('code')}")
                return None
        else:
            print(f"Erreur HTTP: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"Exception lors de l'authentification: {str(e)}")
        return None

def refresh_token(refresh_token):
    """
    Rafraîchit un token d'accès en utilisant le refresh token
    
    Args:
        refresh_token (str): Le refresh token
        
    Returns:
        dict: Nouvelles informations du token ou None en cas d'erreur
    """
    refresh_url = "https://developers.cjdropshipping.com/api2.0/v1/authentication/refreshAccessToken"
    
    payload = {
        "refreshToken": refresh_token
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(refresh_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 200:
                print("Rafraîchissement du token réussi!")
                # Mettre à jour le token stocké
                with open(".token", "w") as token_file:
                    json.dump(data.get('data'), token_file)
                return data.get('data')
            else:
                print(f"Erreur d'API: {data.get('message')}")
                return None
        else:
            print(f"Erreur HTTP: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"Exception lors du rafraîchissement du token: {str(e)}")
        return None

def get_stored_token():
    """
    Récupère le token stocké localement
    
    Returns:
        dict: Informations du token ou None si non trouvé
    """
    try:
        if os.path.exists(".token"):
            with open(".token", "r") as token_file:
                return json.load(token_file)
        return None
    except Exception:
        return None

def main():
    """
    Exemple d'utilisation du script d'authentification
    """
    load_dotenv()
    email = os.getenv('CJDROPSHIPPING_EMAIL')
    api_key = os.getenv('CJDROPSHIPPING_API_KEY')
    
    print("=== Authentification à l'API CJDropshipping ===")
    print(f"Email: {email}")
    print(f"Clé API: {api_key[:5]}...{api_key[-5:] if api_key else ''}")
    
    # Vérifier si nous avons déjà un token stocké
    stored_token = get_stored_token()
    if stored_token:
        print("\nToken stocké trouvé:")
        print(f"Access Token: {stored_token.get('accessToken')[:5]}...{stored_token.get('accessToken')[-5:]}")
        print(f"Expiration: {stored_token.get('accessTokenExpiryDate')}")
        print(f"Refresh Token: {stored_token.get('refreshToken')[:5]}...{stored_token.get('refreshToken')[-5:]}")
        refresh = input("\nVoulez-vous rafraîchir ce token? (o/n): ")
        
        if refresh.lower() == 'o':
            new_token = refresh_token(stored_token.get('refreshToken'))
            if new_token:
                print("\nNouveau token obtenu!")
                print(f"Access Token: {new_token.get('accessToken')[:5]}...{new_token.get('accessToken')[-5:]}")
                print(f"Expiration: {new_token.get('accessTokenExpiryDate')}")
    else:
        # Obtenir un nouveau token
        token_data = get_access_token()
        if token_data:
            print("\nToken d'accès obtenu avec succès!")
            print(f"Access Token: {token_data.get('accessToken')[:5]}...{token_data.get('accessToken')[-5:]}")
            print(f"Expiration: {token_data.get('accessTokenExpiryDate')}")
            print(f"Refresh Token: {token_data.get('refreshToken')[:5]}...{token_data.get('refreshToken')[-5:]}")
        else:
            print("\nÉchec de l'obtention du token.")

if __name__ == "__main__":
    main()
