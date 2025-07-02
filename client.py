"""
Client pour l'API CJDropshipping avec authentification par token
Basé sur la documentation officielle: https://developers.cjdropshipping.cn/en/api/introduction.html
"""
import requests
import json
import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from auth import get_access_token, refresh_token, get_stored_token

class CJDropshippingClient:
    """
    Client pour interagir avec l'API CJDropshipping en utilisant l'authentification par token.
    Supporte les endpoints de l'API v1.
    """
    
    def __init__(self):
        """
        Initialise le client CJDropshipping
        """
        self.base_url = "https://developers.cjdropshipping.com/api2.0/v1"
        self._ensure_valid_token()
    
    def _ensure_valid_token(self):
        """
        S'assure que nous avons un token d'accès valide
        """
        token_data = get_stored_token()
        
        # Si pas de token ou token expiré, en obtenir un nouveau
        if not token_data:
            token_data = get_access_token()
            if not token_data:
                raise Exception("Impossible d'obtenir un token d'accès. Vérifiez vos identifiants.")
        else:
            # Vérifier si le token est expiré
            try:
                expiry_date = datetime.fromisoformat(token_data['accessTokenExpiryDate'].replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                if expiry_date <= now:
                    # Token expiré, essayer de le rafraîchir
                    token_data = refresh_token(token_data['refreshToken'])
                    if not token_data:
                        # Si le rafraîchissement échoue, obtenir un nouveau token
                        token_data = get_access_token()
                        if not token_data:
                            raise Exception("Impossible d'obtenir un nouveau token d'accès.")
            except Exception as e:
                print(f"Erreur lors de la vérification de l'expiration du token: {str(e)}")
                # En cas d'erreur, essayer d'obtenir un nouveau token
                token_data = get_access_token()
                if not token_data:
                    raise Exception("Impossible d'obtenir un token d'accès.")
        
        self.access_token = token_data['accessToken']
    
    def _make_request(self, method, endpoint, params=None, data=None, headers=None):
        """
        Effectue une requête à l'API CJDropshipping
        
        Args:
            method (str): Méthode HTTP (GET, POST, etc.)
            endpoint (str): Endpoint de l'API (sans le /api2.0/v1)
            params (dict, optional): Paramètres de requête
            data (dict, optional): Données pour les requêtes POST
            headers (dict, optional): En-têtes HTTP supplémentaires
            
        Returns:
            dict: Réponse JSON de l'API
            
        Raises:
            Exception: En cas d'erreur HTTP ou d'erreur de l'API
        """
        # S'assurer que nous avons un token valide
        self._ensure_valid_token()
        
        # Construire l'URL
        url = f"{self.base_url}{endpoint}"
        
        # Préparer les en-têtes
        request_headers = {
            "CJ-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
        if headers:
            request_headers.update(headers)
        
        # Effectuer la requête
        response = requests.request(
            method=method,
            url=url,
            headers=request_headers,
            params=params,
            json=data
        )
        
        # Traiter la réponse
        if response.status_code == 200:
            data = response.json()
            if data.get('code') != 200 and data.get('result') is False:
                raise Exception(f"Erreur de l'API: {data.get('message')}, code: {data.get('code')}")
            return data
        else:
            raise Exception(f"Erreur de requête HTTP: {response.status_code}, {response.text}")
    
    # ====== PRODUITS ======
    
    def get_categories(self):
        """
        Récupère la liste des catégories de produits
        
        Returns:
            dict: Catégories de produits
        """
        return self._make_request("GET", "/product/getCategory")
    
    def get_product_list(self, page_num=1, page_size=20, **kwargs):
        """
        Récupère la liste des produits
        
        Args:
            page_num (int): Numéro de page
            page_size (int): Nombre d'éléments par page
            **kwargs: Filtres supplémentaires (categoryId, productName, etc.)
            
        Returns:
            dict: Liste des produits
        """
        params = {
            "pageNum": page_num,
            "pageSize": page_size,
            **kwargs
        }
        
        return self._make_request("GET", "/product/list", params=params)
    
    def get_product_details(self, pid=None, product_sku=None, variant_sku=None):
        """
        Récupère les détails d'un produit
        
        Args:
            pid (str, optional): ID du produit
            product_sku (str, optional): SKU du produit
            variant_sku (str, optional): SKU de la variante
            
        Returns:
            dict: Détails du produit
            
        Raises:
            ValueError: Si aucun identifiant n'est fourni
        """
        if not (pid or product_sku or variant_sku):
            raise ValueError("Vous devez fournir soit pid, product_sku ou variant_sku")
        
        params = {}
        if pid:
            params["pid"] = pid
        elif product_sku:
            params["productSku"] = product_sku
        elif variant_sku:
            params["variantSku"] = variant_sku
        
        return self._make_request("GET", "/product/query", params=params)
    
    def add_to_my_product(self, product_id):
        """
        Ajoute un produit à "Mes produits"
        
        Args:
            product_id (str): ID du produit
            
        Returns:
            dict: Résultat de l'ajout
        """
        data = {
            "productId": product_id
        }
        
        return self._make_request("POST", "/product/addToMyProduct", data=data)
    
    def get_my_products(self, keyword=None, page_num=1, page_size=10, **kwargs):
        """
        Récupère la liste de "Mes produits"
        
        Args:
            keyword (str, optional): Mot-clé de recherche
            page_num (int): Numéro de page
            page_size (int): Nombre d'éléments par page
            **kwargs: Filtres supplémentaires
            
        Returns:
            dict: Liste de "Mes produits"
        """
        params = {
            "pageNumber": page_num,
            "pageSize": page_size
        }
        
        if keyword:
            params["keyword"] = keyword
            
        # Ajouter les filtres supplémentaires
        params.update(kwargs)
        
        return self._make_request("GET", "/product/myProduct/query", params=params)
    
    # ====== VARIANTS ======
    
    def get_variants(self, pid=None, product_sku=None, variant_sku=None, country_code=None):
        """
        Récupère les variantes d'un produit
        
        Args:
            pid (str, optional): ID du produit
            product_sku (str, optional): SKU du produit
            variant_sku (str, optional): SKU de la variante
            country_code (str, optional): Code pays pour filtrer par inventaire
            
        Returns:
            dict: Variantes du produit
            
        Raises:
            ValueError: Si aucun identifiant n'est fourni
        """
        if not (pid or product_sku or variant_sku):
            raise ValueError("Vous devez fournir soit pid, product_sku ou variant_sku")
        
        params = {}
        if pid:
            params["pid"] = pid
        elif product_sku:
            params["productSku"] = product_sku
        elif variant_sku:
            params["variantSku"] = variant_sku
            
        if country_code:
            params["countryCode"] = country_code
        
        return self._make_request("GET", "/product/variant/query", params=params)
    
    def get_variant_by_id(self, vid):
        """
        Récupère une variante par son ID
        
        Args:
            vid (str): ID de la variante
            
        Returns:
            dict: Détails de la variante
        """
        params = {"vid": vid}
        return self._make_request("GET", "/product/variant/queryByVid", params=params)
    
    # ====== INVENTAIRE ======
    
    def get_inventory(self, vid):
        """
        Récupère l'inventaire d'une variante
        
        Args:
            vid (str): ID de la variante
            
        Returns:
            dict: Inventaire de la variante
        """
        params = {"vid": vid}
        return self._make_request("GET", "/product/stock/queryByVid", params=params)
    
    def get_inventory_by_sku(self, sku):
        """
        Récupère l'inventaire par SKU
        
        Args:
            sku (str): SKU du produit ou de la variante
            
        Returns:
            dict: Inventaire
        """
        params = {"sku": sku}
        return self._make_request("GET", "/product/stock/queryBySku", params=params)
    
    # ====== AVIS PRODUITS ======
    
    def get_product_reviews(self, pid, score=None, page_num=1, page_size=20):
        """
        Récupère les avis d'un produit
        
        Args:
            pid (str): ID du produit
            score (int, optional): Score pour filtrer les avis
            page_num (int): Numéro de page
            page_size (int): Nombre d'éléments par page
            
        Returns:
            dict: Avis du produit
        """
        params = {
            "pid": pid,
            "pageNum": page_num,
            "pageSize": page_size
        }
        
        if score is not None:
            params["score"] = score
        
        return self._make_request("GET", "/product/productComments", params=params)
    
    # ====== PARAMÈTRES ======
    
    def get_settings(self):
        """
        Récupère les paramètres du compte
        
        Returns:
            dict: Paramètres du compte
        """
        return self._make_request("GET", "/setting/get")
    
    # ====== COMMANDES ET PAIEMENT ======
    
    def create_order_v2(self, order_data):
        """
        Crée une commande (version 2 de l'API)
        
        Args:
            order_data (dict): Données de la commande, incluant:
                - orderNumber: Identifiant unique de la commande
                - shippingZip: Code postal de livraison
                - shippingCountryCode: Code pays de livraison
                - shippingCountry: Pays de livraison
                - shippingProvince: Province/État de livraison
                - shippingCity: Ville de livraison
                - shippingAddress: Adresse de livraison
                - shippingCustomerName: Nom du client
                - shippingPhone: Téléphone du client
                - logisticName: Nom du service logistique
                - fromCountryCode: Pays d'expédition
                - products: Liste des produits (vid, quantity)
                - et d'autres paramètres optionnels
        
        Returns:
            dict: Informations sur la commande créée
        """
        return self._make_request("POST", "/shopping/order/createOrderV2", data=order_data)
    
    def get_orders(self, page_num=1, page_size=20, **kwargs):
        """
        Récupère la liste des commandes
        
        Args:
            page_num (int): Numéro de page
            page_size (int): Nombre d'éléments par page
            **kwargs: Filtres supplémentaires (orderIds, shipmentOrderId, status)
                - status peut être: CREATED, IN_CART, UNPAID, UNSHIPPED, SHIPPED, DELIVERED, CANCELLED, OTHER
        
        Returns:
            dict: Liste des commandes
        """
        params = {
            "pageNum": page_num,
            "pageSize": page_size
        }
        
        # Ajouter les filtres supplémentaires
        params.update(kwargs)
        
        return self._make_request("GET", "/shopping/order/list", params=params)
    
    def get_order_detail(self, order_id, features=None):
        """
        Récupère les détails d'une commande
        
        Args:
            order_id (str): Identifiant de la commande (peut être un ID personnalisé ou un ID CJ)
            features (list, optional): Fonctionnalités supplémentaires à activer, comme LOGISTICS_TIMELINESS
        
        Returns:
            dict: Détails de la commande
        """
        params = {"orderId": order_id}
        
        if features:
            params["features"] = features
        
        return self._make_request("GET", "/shopping/order/getOrderDetail", params=params)
    
    def delete_order(self, order_id):
        """
        Supprime une commande
        
        Args:
            order_id (str): Identifiant de la commande
        
        Returns:
            dict: Résultat de la suppression
        """
        params = {"orderId": order_id}
        return self._make_request("DELETE", "/shopping/order/deleteOrder", params=params)
    
    def confirm_order(self, order_id):
        """
        Confirme une commande
        
        Args:
            order_id (str): Identifiant de la commande
        
        Returns:
            dict: Résultat de la confirmation
        """
        data = {"orderId": order_id}
        return self._make_request("PATCH", "/shopping/order/confirmOrder", data=data)
    
    # ====== PAIEMENT ======
    
    def get_balance(self):
        """
        Récupère le solde du compte
        
        Returns:
            dict: Informations sur le solde
        """
        return self._make_request("GET", "/shopping/pay/getBalance")
    
    def pay_balance(self, order_id):
        """
        Effectue un paiement par solde pour une commande
        
        Args:
            order_id (str): Identifiant de la commande
        
        Returns:
            dict: Résultat du paiement
        """
        data = {"orderId": order_id}
        return self._make_request("POST", "/shopping/pay/payBalance", data=data)
    
    # ====== GESTION DES COMMANDES ======
    
    def create_order(self, order_data):
        """
        Crée une commande (Version 1 - Obsolète)
        Utilisez plutôt create_order_v2
        
        Args:
            order_data (dict): Données de la commande
            
        Returns:
            dict: Résultat de la création de commande
        """
        return self._make_request("POST", "/shopping/order/createOrder", data=order_data)
    
    def create_order_v2(self, order_data):
        """
        Crée une commande (Version 2 recommandée)
        
        Args:
            order_data (dict): Données de la commande contenant les champs obligatoires:
                - orderNumber: Identifiant unique de la commande
                - shippingZip: Code postal de livraison
                - shippingCountryCode: Code pays de livraison (2 lettres, ex: BF)
                - shippingCountry: Pays de livraison (ex: Burkina Faso)
                - shippingProvince: Province de livraison
                - shippingCity: Ville de livraison
                - shippingPhone: Téléphone du destinataire
                - shippingCustomerName: Nom du destinataire
                - shippingAddress: Adresse de livraison
                - logisticName: Nom du service logistique
                - fromCountryCode: Code pays d'expédition (généralement CN)
                - products: Liste des produits (vid, quantity)
                
        Returns:
            dict: Résultat de la création de commande avec identifiant CJ
        """
        return self._make_request("POST", "/shopping/order/createOrderV2", data=order_data)
    
    def get_order_list(self, page_num=1, page_size=20, status=None, order_ids=None, shipment_order_id=None):
        """
        Récupère la liste des commandes
        
        Args:
            page_num (int): Numéro de page
            page_size (int): Nombre d'éléments par page
            status (str, optional): Statut des commandes à récupérer
                Valeurs possibles: CREATED, IN_CART, UNPAID, UNSHIPPED, SHIPPED, DELIVERED, CANCELLED, OTHER
            order_ids (list, optional): Liste des identifiants de commandes
            shipment_order_id (str, optional): Identifiant d'expédition
            
        Returns:
            dict: Liste des commandes
        """
        params = {
            "pageNum": page_num,
            "pageSize": page_size
        }
        
        if status:
            params["status"] = status
        if order_ids:
            params["orderIds"] = order_ids
        if shipment_order_id:
            params["shipmentOrderId"] = shipment_order_id
            
        return self._make_request("GET", "/shopping/order/list", params=params)
    
    def get_order_detail(self, order_id, features=None):
        """
        Récupère les détails d'une commande
        
        Args:
            order_id (str): Identifiant de la commande (peut être l'ID personnalisé ou l'ID CJ)
            features (list, optional): Fonctionnalités à activer, ex: ["LOGISTICS_TIMELINESS"]
            
        Returns:
            dict: Détails de la commande
        """
        params = {"orderId": order_id}
        
        if features:
            params["features"] = features
            
        return self._make_request("GET", "/shopping/order/getOrderDetail", params=params)
    
    def delete_order(self, order_id):
        """
        Supprime une commande
        
        Args:
            order_id (str): Identifiant de la commande
            
        Returns:
            dict: Résultat de la suppression
        """
        params = {"orderId": order_id}
        return self._make_request("DELETE", "/shopping/order/deleteOrder", params=params)
    
    def confirm_order(self, order_id):
        """
        Confirme une commande
        
        Args:
            order_id (str): Identifiant de la commande
            
        Returns:
            dict: Résultat de la confirmation
        """
        data = {"orderId": order_id}
        return self._make_request("PATCH", "/shopping/order/confirmOrder", data=data)
    
    # ====== LOGISTIQUE ET SUIVI ======
    
    def calculate_shipping(self, start_country_code, end_country_code, products, zip_code=None, tax_id=None, house_number=None, ioss_number=None):
        """
        Calcule les frais d'expédition pour des produits
        
        Args:
            start_country_code (str): Code pays d'origine
            end_country_code (str): Code pays de destination
            products (list): Liste des produits (vid, quantity)
            zip_code (str, optional): Code postal
            tax_id (str, optional): ID fiscal
            house_number (str, optional): Numéro de maison
            ioss_number (str, optional): Numéro IOSS
            
        Returns:
            dict: Options d'expédition disponibles et leurs coûts
        """
        data = {
            "startCountryCode": start_country_code,
            "endCountryCode": end_country_code,
            "products": products
        }
        
        # Ajouter les paramètres optionnels
        if zip_code:
            data["zip"] = zip_code
        if tax_id:
            data["taxId"] = tax_id
        if house_number:
            data["houseNumber"] = house_number
        if ioss_number:
            data["iossNumber"] = ioss_number
            
        return self._make_request("POST", "/logistic/freightCalculate", data=data)
    
    def calculate_shipping_tip(self, req_dtos):
        """
        Calcule les frais d'expédition avec des conseils détaillés
        
        Args:
            req_dtos (list): Liste des requêtes de calcul de frais avec des paramètres détaillés
            
        Returns:
            dict: Options d'expédition détaillées
        """
        data = {"reqDTOS": req_dtos}
        return self._make_request("POST", "/logistic/freightCalculateTip", data=data)
    
    def get_tracking_info(self, tracking_number=None, order_number=None):
        """
        Récupère les informations de suivi d'un colis
        
        Args:
            tracking_number (str, optional): Numéro de suivi
            order_number (str, optional): Numéro de commande
            
        Note:
            Vous devez fournir soit tracking_number soit order_number
            
        Returns:
            dict: Informations de suivi du colis
        """
        if not tracking_number and not order_number:
            raise ValueError("Vous devez fournir soit tracking_number soit order_number")
            
        params = {}
        if tracking_number:
            params["trackNumber"] = tracking_number
        if order_number:
            params["orderNumber"] = order_number
            
        return self._make_request("GET", "/logistic/trackInfo", params=params)
    
    # ====== MÉTHODE DE DEBUG ======
    
    def debug_api(self, endpoint, method="GET", params=None, data=None):
        """
        Méthode de débogage pour tester directement les endpoints de l'API
        
        Args:
            endpoint (str): Endpoint à tester (avec le /api2.0/v1)
            method (str): Méthode HTTP
            params (dict, optional): Paramètres de requête
            data (dict, optional): Données pour les requêtes POST
            
        Returns:
            dict: Réponse de l'API
        """
        # Extraire la partie de l'endpoint après /api2.0/v1 si présent
        if endpoint.startswith("/api2.0/v1"):
            endpoint = endpoint[10:]
        elif endpoint.startswith("api2.0/v1"):
            endpoint = endpoint[8:]
            
        return self._make_request(method, endpoint, params=params, data=data)
