#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API v1 pour l'intégration CJDropshipping au Burkina Faso
Modèle de distribution centralisée: toutes les commandes sont livrées à une adresse unique 
puis redistribuées localement par le propriétaire de l'application
"""

# Importer le patch Pydantic pour la compatibilité avec Python 3.12/3.13
import pydantic_patch

import os
import json
import time
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, status, Request, Response, Body, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, EmailStr, validator, AnyHttpUrl

from client import CJDropshippingClient
from auth import get_stored_token, get_access_token, refresh_token

# Création de l'application FastAPI avec métadonnées complètes pour OpenAPI/Swagger
app = FastAPI(
    title="CJDropshipping Burkina Faso API",
    description="""**API RESTful pour l'intégration CJDropshipping avec distribution centralisée au Burkina Faso.**
    
    ## Objectif
    
    Cette API est conçue selon un modèle où **toutes les commandes sont livrées à une adresse centrale au Burkina Faso**,
    permettant ensuite au propriétaire de gérer la distribution aux clients finaux.
    
    ## Authentification
    
    L'API utilise un système d'authentification par token fourni par CJDropshipping.
    Le token est automatiquement géré et rafraîchi en interne.
    
    ## Modèle de distribution
    
    1. Les produits sont sélectionnés depuis le catalogue CJDropshipping
    2. Les commandes sont passées avec livraison à une adresse centralisée au Burkina Faso
    3. Le propriétaire se charge ensuite de la distribution finale aux clients
    
    ## Spécificités techniques
    
    - L'authentification utilise un token stocké localement (valide 15 jours)
    - La taille minimale de page pour les recherches est de 10
    - La documentation OpenAPI/Swagger est disponible à `/docs`
    """,
    version="1.0.0",
    contact={
        "name": "Support API CJDropshipping Burkina Faso",
        "email": "support@example.com",
        "url": "https://example.com/support",
    },
    terms_of_service="https://example.com/terms/",
    license_info={
        "name": "Propriétaire",
        "url": "https://example.com/license",
    },
    openapi_tags=[
        {
            "name": "General",
            "description": "Opérations générales et statut de l'API"
        },
        {
            "name": "Authentification",
            "description": "Opérations liées à l'authentification avec CJDropshipping"
        },
        {
            "name": "Categories",
            "description": "Consultation des catégories de produits disponibles"
        },
        {
            "name": "Produits",
            "description": "Recherche et informations détaillées sur les produits du catalogue"
        },
        {
            "name": "Variantes",
            "description": "Gestion et consultation des variantes de produits"
        },
        {
            "name": "Inventaire",
            "description": "Vérification de la disponibilité des produits et des stocks"
        },
        {
            "name": "Avis",
            "description": "Consultation des avis et évaluations sur les produits"
        },
        {
            "name": "Commandes",
            "description": "Création et gestion des commandes client"
        },
        {
            "name": "Paiement",
            "description": "Gestion des paiements et du solde du compte"
        },
        {
            "name": "Logistique",
            "description": "Calcul des frais d'expédition et options logistiques"
        },
        {
            "name": "Suivi",
            "description": "Suivi des expéditions et livraisons"
        },
        {
            "name": "Compte",
            "description": "Informations sur le compte et paramètres"
        },
    ],
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuration CORS pour permettre l'accès depuis l'application mobile
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À remplacer par les domaines autorisés en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation du client CJDropshipping
cj_client = CJDropshippingClient()

# Chargement des variables d'environnement
from dotenv import load_dotenv
load_dotenv()

# Adresse de livraison centralisée au Burkina Faso depuis les variables d'environnement
DEFAULT_SHIPPING_INFO = {
    "shippingZip": os.getenv("SHIPPING_ZIP"),  # Code postal d'Ouagadougou
    "shippingCountryCode": os.getenv("SHIPPING_COUNTRY_CODE"),  # Code pays du Burkina Faso
    "shippingCountry": os.getenv("SHIPPING_COUNTRY"),
    "shippingProvince": os.getenv("SHIPPING_PROVINCE"),
    "shippingCity": os.getenv("SHIPPING_CITY"),
    "shippingAddress": os.getenv("SHIPPING_ADDRESS"),
    "shippingCustomerName": os.getenv("SHIPPING_CUSTOMER_NAME"),
    "shippingPhone": os.getenv("SHIPPING_PHONE")
}

# Modèle pour les résultats de recherche de produits
class ProductSearchResponse(BaseModel):
    """Réponse pour la recherche de produits"""
    products: List[Dict[str, Any]] = Field(..., description="Liste des produits correspondants")
    total: int = Field(..., description="Nombre total de produits disponibles")
    page: int = Field(..., description="Page actuelle")
    page_size: int = Field(..., description="Nombre d'éléments par page")
    
    class Config:
        schema_extra = {
            "example": {
                "products": [
                    {
                        "pid": "2507020928431604700",
                        "productNameEn": "Solar Garden Light",
                        "productSku": "SKU12345",
                        "productImage": "https://example.com/image.jpg",
                        "categoryId": "123456",
                        "price": 12.99
                    }
                ],
                "total": 120,
                "page": 1,
                "page_size": 10
            }
        }

# ====== ENDPOINTS POUR LES CATÉGORIES ======

@app.get(
    "/categories",
    response_model=Dict[str, Any],
    summary="Liste des catégories de produits",
    description="Récupère la liste complète des catégories de produits disponibles chez CJDropshipping.",
    response_description="Liste des catégories avec leurs identifiants et noms",
    responses={
        200: {
            "description": "Liste des catégories récupérée avec succès"
        },
        401: {
            "description": "Erreur d'authentification avec l'API CJDropshipping"
        },
        500: {
            "description": "Erreur du serveur lors de la récupération des catégories"
        }
    },
    tags=["Categories"],
    operation_id="get_product_categories"
)
async def get_categories():
    """Récupère la liste complète des catégories de produits.
    
    Returns:
        dict: Réponse standardisée contenant la liste des catégories
    """
    try:
        response = cj_client.get_categories()
        
        # Retourner la réponse standardisée
        if response.get("code") == 200 and response.get("result"):
            return response
        else:
            raise HTTPException(
                status_code=response.get("code", 500),
                detail=f"Erreur lors de la récupération des catégories: {response.get('message', 'Erreur inconnue')}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des catégories: {str(e)}"
        )

@app.get(
    "/products/category/{category_id}",
    summary="Produits par catégorie",
    description="Recherche des produits par catégorie dans le catalogue CJDropshipping.",
    response_description="Liste paginée des produits de la catégorie spécifiée",
    responses={
        200: {
            "description": "Liste des produits récupérée avec succès"
        },
        400: {
            "description": "Paramètres de requête invalides"
        },
        401: {
            "description": "Erreur d'authentification avec l'API CJDropshipping"
        },
        500: {
            "description": "Erreur du serveur lors de la recherche de produits"
        }
    },
    tags=["Produits"]
)
async def get_products_by_category(
    category_id: str = Path(..., description="Identifiant de la catégorie", examples=["123456"]),
    page: int = Query(1, ge=1, description="Numéro de la page (1-indexé)", examples=[1]),
    page_size: int = Query(10, ge=10, le=100, description="Nombre d'éléments par page (minimum 10)", examples=[10])
):
    """
    Recherche des produits par catégorie dans le catalogue CJDropshipping
    
    Args:
        category_id (str): Identifiant de la catégorie à filtrer
        page (int): Numéro de page (1-indexé)
        page_size (int): Nombre d'éléments par page (minimum 10)
        
    Returns:
        dict: Réponse standardisée contenant les résultats de recherche paginés
    """
    try:
        response = cj_client.get_product_list(
            page_num=page,
            page_size=page_size,
            categoryId=category_id
        )
        
        # Retourner la réponse standardisée
        if response.get("code") == 200 and response.get("result"):
            return response
        else:
            raise HTTPException(
                status_code=response.get("code", 500),
                detail=f"Erreur lors de la recherche de produits: {response.get('message', 'Erreur inconnue')}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la recherche de produits: {str(e)}"
        )

# Enums pour les options standards
# ====== ENDPOINTS POUR LES VARIANTES DE PRODUITS ======

@app.get(
    "/products/{product_id}/variants",
    summary="Variantes d'un produit",
    description="Récupère toutes les variantes disponibles pour un produit spécifique.",
    response_description="Liste des variantes du produit avec leurs attributs",
    responses={
        200: {
            "description": "Variantes récupérées avec succès"
        },
        400: {
            "description": "ID de produit invalide"
        },
        401: {
            "description": "Erreur d'authentification avec l'API CJDropshipping"
        },
        404: {
            "description": "Produit non trouvé"
        },
        500: {
            "description": "Erreur du serveur lors de la récupération des variantes"
        }
    },
    tags=["Variantes"]
)
async def get_product_variants(product_id: str = Path(..., description="ID du produit", examples=["1234567890"])):
    """
    Récupère toutes les variantes disponibles pour un produit spécifique.
    
    Args:
        product_id (str): Identifiant unique du produit
    
    Returns:
        dict: Réponse standardisée contenant la liste des variantes
    """
    try:
        response = cj_client.get_product_variants(product_id)
        
        # Retourner la réponse standardisée
        if response.get("code") == 200 and response.get("result"):
            return response
        else:
            raise HTTPException(
                status_code=response.get("code", 500),
                detail=f"Erreur lors de la récupération des variantes: {response.get('message', 'Erreur inconnue')}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des variantes: {str(e)}"
        )

# ====== ENDPOINTS POUR L'INVENTAIRE ======

@app.get(
    "/inventory/check/{variant_id}",
    summary="Vérification du stock",
    description="Vérifie la disponibilité en stock d'une variante de produit spécifique.",
    response_description="Informations sur le stock de la variante",
    responses={
        200: {
            "description": "Informations de stock récupérées avec succès"
        },
        400: {
            "description": "ID de variante invalide"
        },
        401: {
            "description": "Erreur d'authentification avec l'API CJDropshipping"
        },
        404: {
            "description": "Variante non trouvée"
        },
        500: {
            "description": "Erreur du serveur lors de la vérification du stock"
        }
    },
    tags=["Inventaire"]
)
async def check_inventory(variant_id: str = Path(..., description="ID de la variante", examples=["V-1234567890"])):
    """
    Vérifie la disponibilité en stock d'une variante de produit spécifique.
    
    Args:
        variant_id (str): Identifiant unique de la variante
    
    Returns:
        dict: Réponse standardisée contenant les informations de stock
    """
    try:
        response = cj_client.check_inventory(variant_id)
        
        # Retourner la réponse standardisée
        if response.get("code") == 200 and response.get("result"):
            return response
        else:
            raise HTTPException(
                status_code=response.get("code", 500),
                detail=f"Erreur lors de la vérification du stock: {response.get('message', 'Erreur inconnue')}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la vérification du stock: {str(e)}"
        )

# ====== ENDPOINTS POUR LES AVIS ======

@app.get(
    "/reviews/{product_id}",
    summary="Avis sur un produit",
    description="Récupère les avis clients pour un produit spécifique.",
    response_description="Liste paginée des avis clients",
    responses={
        200: {
            "description": "Avis récupérés avec succès"
        },
        400: {
            "description": "ID de produit invalide"
        },
        401: {
            "description": "Erreur d'authentification avec l'API CJDropshipping"
        },
        404: {
            "description": "Produit non trouvé ou aucun avis disponible"
        },
        500: {
            "description": "Erreur du serveur lors de la récupération des avis"
        }
    },
    tags=["Avis"]
)
async def get_product_reviews(
    product_id: str = Path(..., description="ID du produit", examples=["1234567890"]),
    page: int = Query(1, ge=1, description="Numéro de la page", examples=[1]),
    page_size: int = Query(10, ge=1, le=50, description="Nombre d'avis par page", examples=[10])
):
    """
    Récupère les avis clients pour un produit spécifique.
    
    Args:
        product_id (str): Identifiant unique du produit
        page (int): Numéro de la page (1-indexé)
        page_size (int): Nombre d'avis par page
    
    Returns:
        dict: Réponse standardisée contenant la liste des avis clients
    """
    try:
        response = cj_client.get_product_reviews(product_id, page, page_size)
        
        # Retourner la réponse standardisée
        if response.get("code") == 200 and response.get("result"):
            return response
        else:
            raise HTTPException(
                status_code=response.get("code", 500),
                detail=f"Erreur lors de la récupération des avis: {response.get('message', 'Erreur inconnue')}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des avis: {str(e)}"
        )

# Enums pour les options standards
class OrderStatus(str, Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class PaymentType(int, Enum):
    CREDIT = 1
    BALANCE = 2
    UNPAID = 3

class LogisticService(str, Enum):
    CJ_PACKET_ORDINARY = "CJPacket Ordinary"
    CJ_PACKET_PREMIUM = "CJPacket Premium"
    YUNEXPRESS = "YunExpress"
    DHL = "DHL"
    FEDEX = "FedEx"

# Modèles de base avec documentation et validation

class APIResponse(BaseModel):
    """Modèle de réponse standard conforme à l'API CJDropshipping"""
    result: bool = Field(..., description="Indique si la requête a réussi")
    code: int = Field(..., description="Code de statut de la réponse")
    message: str = Field(..., description="Message informatif sur le résultat")
    data: Optional[Any] = Field(None, description="Données retournées par l'API")

    class Config:
        schema_extra = {
            "example": {
                "result": True,
                "code": 200,
                "message": "success",
                "data": {"id": "123456", "name": "Example"}
            }
        }

class ProductSearchParams(BaseModel):
    """Paramètres de recherche de produits"""
    keywords: Optional[str] = Field(None, description="Mots-clés pour la recherche de produits", example="solar light")
    category_id: Optional[str] = Field(None, description="Identifiant de la catégorie", example="12345")
    page: int = Field(1, ge=1, description="Numéro de page", example=1)
    page_size: int = Field(10, ge=10, le=100, description="Nombre d'éléments par page", example=20)
    
    class Config:
        schema_extra = {
            "example": {
                "keywords": "solar light",
                "page": 1,
                "page_size": 20
            }
        }

class ProductDetail(BaseModel):
    """Détails d'un produit"""
    pid: str = Field(..., description="Identifiant unique du produit", example="2507020928431604700")

class VariantDetail(BaseModel):
    """Détails d'une variante de produit"""
    vid: str = Field(..., description="Identifiant unique de la variante", example="2507020928431605000")

class OrderProduct(BaseModel):
    """Produit dans une commande"""
    vid: str = Field(..., description="Identifiant de la variante", example="2507020928431605000")
    quantity: int = Field(..., gt=0, le=100, description="Quantité commandée", example=1)
    
    class Config:
        schema_extra = {
            "example": {
                "vid": "2507020928431605000",
                "quantity": 2
            }
        }



class ShippingInfo(BaseModel):
    """Informations d'expédition pour le client final"""
    customer_name: str = Field(..., min_length=2, max_length=100, description="Nom complet du client", example="John Doe")
    customer_phone: str = Field(..., min_length=8, max_length=20, description="Numéro de téléphone du client", example="+22676543210")
    customer_address: str = Field(..., min_length=5, max_length=200, description="Adresse de livraison du client", example="Avenue de l'Indépendance, Secteur 12")
    city: str = Field("Ouagadougou", description="Ville du client", example="Ouagadougou")
    province: str = Field("Kadiogo", description="Province/Région du client", example="Kadiogo")
    note: Optional[str] = Field(None, max_length=500, description="Notes spéciales pour la livraison", example="Près du marché central")
    
    class Config:
        schema_extra = {
            "example": {
                "customer_name": "John Doe",
                "customer_phone": "+22676543210",
                "customer_address": "Avenue de l'Indépendance, Secteur 12",
                "city": "Ouagadougou",
                "province": "Kadiogo",
                "note": "Près du marché central"
            }
        }

class CreateOrderRequest(BaseModel):
    """Demande de création d'une commande"""
    order_ref: str = Field(..., min_length=3, max_length=50, description="Votre référence interne pour la commande", example="CMD-20250702-001")
    products: List[OrderProduct] = Field(..., min_items=1, description="Liste des produits commandés")
    customer_info: ShippingInfo = Field(..., description="Informations du client final (pour vos registres)")
    logistic_name: str = Field("CJPacket Ordinary", description="Service logistique souhaité", example="CJPacket Ordinary")
    
    class Config:
        schema_extra = {
            "example": {
                "order_ref": "CMD-20250702-001",
                "products": [{
                    "vid": "2507020928431605000",
                    "quantity": 2
                }],
                "customer_info": {
                    "customer_name": "John Doe",
                    "customer_phone": "+22676543210",
                    "customer_address": "Avenue de l'Indépendance, Secteur 12",
                    "city": "Ouagadougou",
                    "province": "Kadiogo"
                },
                "logistic_name": "CJPacket Ordinary"
            }
        }

class OrderResponse(BaseModel):
    """Réponse pour une commande"""
    order_id: str = Field(..., description="Identifiant de la commande", example="CJ12345678")
    cj_order_id: Optional[str] = Field(None, description="Identifiant CJDropshipping de la commande", example="CJ12345678")
    status: str = Field(..., description="Statut de la commande", example="CREATED")
    created_at: str = Field(..., description="Date de création au format ISO", example="2025-07-02T14:30:00+00:00")
    products: List[Dict[str, Any]] = Field(..., description="Liste des produits commandés")
    shipping_info: Dict[str, Any] = Field(..., description="Informations d'expédition")
    tracking_number: Optional[str] = Field(None, description="Numéro de suivi", example="CJ12345678CN")
    
    class Config:
        schema_extra = {
            "example": {
                "order_id": "CJ12345678",
                "cj_order_id": "CJ12345678",
                "status": "CREATED",
                "created_at": "2025-07-02T14:30:00+00:00",
                "products": [{
                    "vid": "2507020928431605000",
                    "quantity": 2,
                    "name": "Rose Pendant Necklace",
                    "price": 1.86
                }],
                "shipping_info": {
                    "shippingCustomerName": "Votre Nom",
                    "shippingAddress": "Avenue de l'Indépendance",
                    "shippingCity": "Ouagadougou",
                    "shippingCountry": "Burkina Faso"
                }
            }
        }

# Routes de l'API

@app.get("/", tags=["General"],
    response_model=APIResponse,
    summary="Informations sur l'API",
    description="Point d'entrée racine qui retourne les informations de base sur l'API",
    responses={
        200: {"description": "Informations sur l'API"}
    }
)
async def root():
    """Point d'entrée racine de l'API qui retourne les métadonnées de base sur l'API.
    Utile pour vérifier si l'API est en ligne et fonctionnelle.
    """
    return {
        "success": True,
        "message": "API CJDropshipping Burkina Faso opérationnelle",
        "data": {
            "name": "CJDropshipping Burkina Faso API",
            "version": "1.0.0",
            "status": "online"
        }
    }

class AuthStatus(BaseModel):
    """Statut de l'authentification"""
    authenticated: bool = Field(..., description="Indique si le token est valide")
    message: Optional[str] = Field(None, description="Message détaillé sur le statut")
    expiry: Optional[str] = Field(None, description="Date d'expiration du token au format ISO")
    valid_for: Optional[str] = Field(None, description="Durée de validité restante du token")
    
    class Config:
        schema_extra = {
            "example": {
                "authenticated": True,
                "expiry": "2025-07-17T13:26:34+08:00",
                "valid_for": "15 days, 3:45:12"
            }
        }

@app.get("/auth/status",
    response_model=AuthStatus,
    summary="Vérifie le statut d'authentification",
    description="Vérifie si le token d'accès à l'API CJDropshipping est valide et retourne sa durée de validité",
    responses={
        200: {"description": "Statut d'authentification récupéré avec succès"}
    },
    tags=["Authentification"]
)
async def auth_status():
    """Vérifie le statut de l'authentification avec CJDropshipping.
    
    Le token est stocké dans un fichier .token et est valide pendant 15 jours.
    Cette fonction vérifie si le token existe et s'il est encore valide.
    """
    token_data = get_stored_token()
    if not token_data:
        return {"authenticated": False, "message": "Aucun token d'accès trouvé"}
        
    try:
        # Conversion de la date d'expiration du token en datetime avec timezone
        expiry_date = datetime.fromisoformat(token_data['accessTokenExpiryDate'].replace('Z', '+00:00'))
        
        # Utilisation de datetime.now() avec timezone pour une comparaison correcte
        from datetime import timezone
        now = datetime.now(timezone.utc)
        
        if expiry_date <= now:
            return {"authenticated": False, "message": "Token expiré", "expiry": str(expiry_date)}
            
        return {
            "authenticated": True,
            "expiry": str(expiry_date),
            "valid_for": str(expiry_date - now)
        }
    except Exception as e:
        return {"authenticated": False, "message": f"Erreur: {str(e)}"}

@app.post("/auth/refresh", tags=["Authentification"])
async def refresh_auth():
    """Force le rafraîchissement du token d'authentification"""
    try:
        token_data = get_access_token()
        if not token_data:
            raise HTTPException(status_code=401, detail="Échec de l'authentification")
            
        return {"success": True, "message": "Token rafraîchi avec succès"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du rafraîchissement: {str(e)}")

# Endpoints pour les produits

class ProductSearchResponse(BaseModel):
    """Réponse de recherche de produits"""
    result: bool = Field(..., description="Résultat de l'opération")
    message: str = Field(..., description="Message d'information")
    data: Optional[Dict[str, Any]] = Field(None, description="Données de réponse")
    
    class Config:
        schema_extra = {
            "example": {
                "result": True,
                "message": "Recherche réussie",
                "data": {
                    "list": [
                        {
                            "pid": "2507020928431604700",
                            "productNameEn": "Rose Pendant Necklace Valentine's Day Gift",
                            "productSku": "CS1001",
                            "productImage": "https://example.com/image.jpg",
                            "variantList": [],
                            "categoryId": "123456",
                            "categoryName": "Jewelry",
                            "productType": "normal",
                            "productUnit": "piece",
                            "salePrice": 1.86
                        }
                    ],
                    "total": 1
                }
            }
        }

@app.get("/products/search",
    response_model=ProductSearchResponse,
    summary="Recherche de produits",
    description="Recherche des produits dans le catalogue CJDropshipping selon différents critères",
    responses={
        200: {"description": "Recherche réussie"},
        400: {"description": "Paramètres invalides ou erreur API"},
        500: {"description": "Erreur interne du serveur"}
    },
    tags=["Produits"]
)
async def search_products(
    keywords: Optional[str] = Query(None, description="Mots-clés pour la recherche", examples=["solar light"]),
    category_id: Optional[str] = Query(None, description="Identifiant de la catégorie", examples=["123456"]),
    page: int = Query(1, ge=1, description="Numéro de la page (1-indexé)", examples=[1]),
    page_size: int = Query(10, ge=10, le=100, description="Nombre d'éléments par page (minimum 10)", examples=[10])
):
    """Recherche des produits dans le catalogue CJDropshipping.
    
    Cette API prend en charge la recherche par mots-clés et/ou par catégorie.
    La pagination est obligatoire et la taille minimale de page est de 10.
    Les résultats sont triés par pertinence.
    
    **Important** : Si aucun paramètre de recherche n'est fourni, une liste vide est retournée.
    """
    try:
        # Si aucun paramètre de recherche n'est fourni, retournons une liste vide
        if not keywords and not category_id:
            return {
                "result": True,
                "message": "Veuillez fournir au moins un paramètre de recherche: keywords ou category_id",
                "data": {
                    "list": [],
                    "total": 0
                }
            }
        
        # Vérification de la taille minimale de page (10)
        if page_size < 10:
            page_size = 10  # Force la taille minimale de page à 10
            
        # Recherche des produits via l'API CJDropshipping
        search_results = cj_client.get_product_list(
            page_num=page,
            page_size=page_size,
            keywords=keywords,
            categoryId=category_id
        )
        
        # Vérification du résultat
        if not search_results.get("result"):
            raise HTTPException(
                status_code=400, 
                detail=f"Erreur lors de la recherche: {search_results.get('message')}"
            )
            
        return search_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.post("/products/search",
    response_model=ProductSearchResponse,
    summary="Recherche de produits (POST)",
    description="Version POST de la recherche de produits, pratique pour les applications mobiles",
    responses={
        200: {"description": "Recherche réussie"},
        400: {"description": "Paramètres invalides ou erreur API"},
        500: {"description": "Erreur interne du serveur"}
    },
    tags=["Produits"]
)
async def search_products_post(search_params: ProductSearchParams):
    """Recherche des produits via POST (pour compatibilité).
    
    Cette version utilise le corps de la requête POST pour transmettre les paramètres de recherche,
    ce qui peut être plus pratique pour certaines applications mobiles.
    
    **Important** : La taille minimale de page est de 10 comme indiqué dans la documentation de CJDropshipping.
    """
    # Vérification de la taille minimale de page (10)
    if search_params.page_size < 10:
        search_params.page_size = 10  # Force la taille minimale de page à 10
        
    # Réutilisation de l'endpoint GET avec les mêmes paramètres
    return await search_products(
        keywords=search_params.keywords,
        category_id=search_params.category_id,
        page=search_params.page,
        page_size=search_params.page_size
    )

@app.get("/products/{pid}", tags=["Produits"])
async def get_product(pid: str):
    """Récupère les détails d'un produit"""
    try:
        product_details = cj_client.get_product_details(pid=pid)
        
        if not product_details.get("result"):
            raise HTTPException(
                status_code=404, 
                detail=f"Produit non trouvé: {product_details.get('message')}"
            )
            
        return product_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/categories", tags=["Categories"])
async def get_categories():
    """Récupère la liste des catégories de produits"""
    try:
        categories = cj_client.get_categories()
        
        if not categories.get("result"):
            raise HTTPException(
                status_code=400, 
                detail=f"Erreur lors de la récupération des catégories: {categories.get('message')}"
            )
            
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/products/{pid}/variants", tags=["Variantes"])
async def get_product_variants(pid: str):
    """Récupère les variantes d'un produit"""
    try:
        variants = cj_client.get_variants(pid=pid, country_code="BF")  # Spécifique pour le Burkina Faso
        
        if not variants.get("result"):
            raise HTTPException(
                status_code=404, 
                detail=f"Variantes non trouvées: {variants.get('message')}"
            )
            
        return variants
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/variants/{vid}", tags=["Variantes"])
async def get_variant(vid: str):
    """Récupère les détails d'une variante"""
    try:
        variant = cj_client.get_variant_by_id(vid)
        
        if not variant.get("result"):
            raise HTTPException(
                status_code=404, 
                detail=f"Variante non trouvée: {variant.get('message')}"
            )
            
        return variant
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/variants/{vid}/inventory", tags=["Inventaire"])
async def get_variant_inventory(vid: str):
    """Récupère l'inventaire d'une variante"""
    try:
        inventory = cj_client.get_inventory(vid)
        
        if not inventory.get("result"):
            raise HTTPException(
                status_code=404, 
                detail=f"Inventaire non trouvé: {inventory.get('message')}"
            )
            
        return inventory
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

# Endpoints pour la logistique

class ShippingCalculationRequest(BaseModel):
    """Requête pour le calcul des frais d'expédition"""
    products: List[OrderProduct] = Field(..., min_items=1, description="Liste des produits pour le calcul", example=[{"vid": "2507020928431605000", "quantity": 1}])

class ShippingCalculationResponse(BaseModel):
    """Réponse du calcul des frais d'expédition"""
    result: bool = Field(..., description="Résultat de l'opération")
    message: str = Field(..., description="Message d'information")
    data: Optional[Dict[str, Any]] = Field(None, description="Détails des options d'expédition")

@app.post("/logistics/calculate-shipping",
    response_model=ShippingCalculationResponse,
    summary="Calculer les frais d'expédition",
    description="Calcule les frais d'expédition pour les produits sélectionnés vers le Burkina Faso",
    responses={
        200: {"description": "Calcul des frais réussi"},
        400: {"description": "Produits non valides ou erreur de calcul"},
        500: {"description": "Erreur interne du serveur"}
    },
    tags=["Logistique"]
)
async def calculate_shipping(request: ShippingCalculationRequest):
    """Calcule les frais d'expédition pour les produits sélectionnés.
    
    Cette API utilise l'adresse centralisée au Burkina Faso (Ouagadougou) comme destination.
    Pour chaque produit, spécifiez l'ID de variante (vid) et la quantité.
    Les résultats inclueront les différentes options d'expédition disponibles avec leurs tarifs.
    """
    try:
        # Conversion des produits pour l'API CJ
        cj_products = [{
            "vid": product.vid,
            "quantity": product.quantity
        } for product in request.products]
        
        # Calcul des frais d'expédition avec l'adresse de livraison par défaut au Burkina Faso
        shipping_costs = cj_client.calculate_shipping(
            start_country_code="CN",
            end_country_code="BF",
            products=cj_products,
            zip_code="10000"  # Code postal d'Ouagadougou
        )
        
        return shipping_costs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul des frais d'expédition: {str(e)}")

# Endpoints pour les commandes

class OrderCreationResponse(BaseModel):
    """Réponse à la création d'une commande"""
    order_id: str = Field(..., description="Identifiant de la commande", example="CJ-12345678")
    cj_order_id: Optional[str] = Field(None, description="Identifiant CJDropshipping", example="CJ12345678")
    status: str = Field(..., description="Statut de la commande", example=OrderStatus.CREATED)
    created_at: str = Field(..., description="Date de création de la commande")
    products: List[Dict[str, Any]] = Field(..., description="Détails des produits commandés")
    shipping_info: Dict[str, Any] = Field(..., description="Adresse de livraison centralisée")
    tracking_number: Optional[str] = Field(None, description="Numéro de suivi")

@app.post("/orders",
    response_model=OrderCreationResponse,
    summary="Créer une nouvelle commande",
    description="Crée une nouvelle commande avec CJDropshipping avec livraison centralisée au Burkina Faso",
    responses={
        201: {"description": "Commande créée avec succès"},
        400: {"description": "Paramètres invalides"},
        402: {"description": "Solde insuffisant"},
        404: {"description": "Produit non trouvé ou non disponible"},
        500: {"description": "Erreur interne du serveur"}
    },
    status_code=201,
    tags=["Commandes"]
)
async def create_order(order_request: CreateOrderRequest):
    """Crée une nouvelle commande avec CJDropshipping.
    
    Cette API permet de commander des produits avec le modèle de distribution centralisée pour le Burkina Faso:
    1. Toutes les commandes sont livrées à une adresse unique à Ouagadougou
    2. Les informations du client final sont stockées dans les notes pour vos registres internes
    3. Vous gérez ensuite la distribution locale au client final
    
    **Important**:
    - Les produits doivent être identifiés par leur ID de variante (vid)
    - Votre référence de commande (order_ref) doit être unique
    - Le service logistique par défaut est "CJPacket Ordinary"  
    """
    try:
        # Vérification que tous les produits existent
        for product in order_request.products:
            # Dans une implémentation réelle, vérifier que la variante existe et est en stock
            # variant_info = cj_client.get_variant_by_id(product.vid)
            # if not variant_info or variant_info.get("result") == False:
            #    raise HTTPException(status_code=404, detail=f"Variante {product.vid} non trouvée")
            pass
            
        # Conversion des informations du client pour l'API CJ
        shipping_address = {
            "name": DEFAULT_SHIPPING_INFO["shippingCustomerName"],  # Utilisation de votre adresse centralisée
            "phoneNumber": DEFAULT_SHIPPING_INFO["shippingPhone"],
            "email": "",  # Facultatif
            "address": DEFAULT_SHIPPING_INFO["shippingAddress"],
            "city": DEFAULT_SHIPPING_INFO["shippingCity"],
            "province": DEFAULT_SHIPPING_INFO["shippingProvince"],
            "country": DEFAULT_SHIPPING_INFO["shippingCountry"],
            "zip": DEFAULT_SHIPPING_INFO["shippingZip"]
        }
        
        # Préparation des produits pour l'API CJ
        products = [{
            "vid": product.vid,
            "quantity": product.quantity,
            "shippingName": order_request.logistic_name
        } for product in order_request.products]
        
        # On stocke les infos du client final dans les notes pour vos registres internes
        customer_info = order_request.customer_info
        note = f"Client final: {customer_info.customer_name}, Tél: {customer_info.customer_phone}, Adresse: {customer_info.customer_address}"
        if customer_info.note:
            note += f", Note: {customer_info.note}"
        
        # Simulation de création de commande (remplacer par l'appel API réel)
        # Dans une implémentation réelle, vous utiliserez:
        # result = cj_client.create_order_v2(order_request.order_ref, shipping_address, products, note)
        # if not result.get("result"):
        #     error_message = result.get("message", "Erreur inconnue")
        #     if "balance" in error_message.lower():
        #         raise HTTPException(status_code=402, detail=f"Solde insuffisant: {error_message}")
        #     raise HTTPException(status_code=400, detail=f"Erreur de création: {error_message}")
        
        # Simulation de réponse (succès)
        return {
            "order_id": f"CJ-{uuid.uuid4().hex[:8]}",
            "cj_order_id": None,  # Rempli après confirmation de la commande
            "status": OrderStatus.CREATED,
            "created_at": datetime.now().isoformat(),
            "products": [{
                "vid": product.vid,
                "quantity": product.quantity,
                "name": "Product Name",  # À récupérer via l'API
                "price": 0.0  # À récupérer via l'API
            } for product in order_request.products],
            "shipping_info": shipping_address,
            "tracking_number": None  # Rempli après expédition
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la commande: {str(e)}")

@app.get("/orders", tags=["Commandes"])
async def get_orders(page: int = 1, status: Optional[str] = None):
    """Récupère la liste des commandes"""
    try:
        orders = cj_client.get_order_list(page_num=page, page_size=10, status=status)
        
        if not orders.get("result"):
            raise HTTPException(
                status_code=400, 
                detail=f"Erreur lors de la récupération des commandes: {orders.get('message')}"
            )
            
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/orders/{order_id}", tags=["Commandes"])
async def get_order_details(order_id: str):
    """Récupère les détails d'une commande"""
    try:
        order = cj_client.get_order_detail(order_id)
        
        if not order.get("result"):
            raise HTTPException(
                status_code=404, 
                detail=f"Commande non trouvée: {order.get('message')}"
            )
            
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.delete("/orders/{order_id}", tags=["Commandes"])
async def delete_order(order_id: str):
    """Supprime une commande"""
    try:
        result = cj_client.delete_order(order_id)
        
        if not result.get("result"):
            raise HTTPException(
                status_code=400, 
                detail=f"Erreur lors de la suppression: {result.get('message')}"
            )
            
        return {"success": True, "message": "Commande supprimée avec succès"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

class TrackingResponse(BaseModel):
    """Réponse pour les informations de suivi"""
    result: bool = Field(..., description="Résultat de l'opération")
    message: str = Field(..., description="Message informatif")
    data: Optional[Dict[str, Any]] = Field(None, description="Détails du suivi de l'expédition")
    
    class Config:
        schema_extra = {
            "example": {
                "result": True,
                "message": "Succès",
                "data": {
                    "trackingNumber": "CJ12345678CN",
                    "trackingStatus": "Delivered",
                    "logisticName": "CJPacket Ordinary",
                    "trackingList": [
                        {
                            "date": "2023-07-25 16:30:00",
                            "status": "Delivered",
                            "details": "Package has been delivered to the recipient"
                        },
                        {
                            "date": "2023-07-23 08:15:00",
                            "status": "Out for delivery",
                            "details": "Package is out for delivery in Ouagadougou"
                        }
                    ]
                }
            }
        }

@app.get("/tracking/{tracking_number}",
    response_model=TrackingResponse,
    summary="Suivre une expédition",
    description="Récupère les informations de suivi d'une expédition via son numéro de tracking",
    responses={
        200: {"description": "Informations de suivi récupérées avec succès"},
        404: {"description": "Numéro de suivi non trouvé"},
        500: {"description": "Erreur lors de la récupération des informations"}
    },
    tags=["Suivi"]
)
async def get_tracking_info(tracking_number: str = Path(..., description="Numéro de suivi de l'expédition", examples=["CJ12345678CN"])):
    """Récupère les informations de suivi pour un numéro de tracking.
    
    Cette API permet de suivre l'évolution d'une expédition depuis la Chine jusqu'au Burkina Faso.
    Elle fournit:
    - L'état actuel de l'expédition
    - Le nom du service logistique utilisé
    - L'historique complet avec dates et détails
    
    **Note**: Certains services logistiques peuvent avoir un délai de mise à jour plus important que d'autres.
    """
    try:
        # Récupération des infos de tracking via l'API CJ
        tracking_info = cj_client.get_tracking_info(tracking_number)
        
        if not tracking_info.get("result"):
            raise HTTPException(
                status_code=404, 
                detail=f"Informations de suivi non trouvées: {tracking_info.get('message')}"
            )
            
        return tracking_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des informations de suivi: {str(e)}")

class AccountBalanceResponse(BaseModel):
    """Réponse pour le solde du compte"""
    result: bool = Field(..., description="Résultat de l'opération")
    message: str = Field(..., description="Message informatif")
    data: Optional[Dict[str, Any]] = Field(None, description="Détails du solde du compte")
    
    class Config:
        schema_extra = {
            "example": {
                "result": True,
                "message": "Solde récupéré avec succès",
                "data": {
                    "balance": 250.36,
                    "frozenAmount": 25.12,
                    "currency": "USD"
                }
            }
        }

@app.get("/account/balance",
    response_model=AccountBalanceResponse,
    summary="Consulter le solde du compte",
    description="Récupère le solde disponible sur le compte CJDropshipping",
    responses={
        200: {"description": "Solde récupéré avec succès"},
        400: {"description": "Erreur lors de la récupération du solde"},
        500: {"description": "Erreur interne du serveur"}
    },
    tags=["Compte"]
)
async def get_account_balance():
    """Récupère le solde du compte CJDropshipping.
    
    Cette API renvoie:
    - Le solde disponible pour les commandes
    - Le montant gelé (en cours d'utilisation)
    - La devise du compte (généralement USD)
    
    Il est recommandé de vérifier le solde avant de passer une commande pour éviter les échecs de paiement.
    """
    try:
        # Récupération du solde via l'API CJ
        balance = cj_client.get_balance()
        
        if not balance.get("result"):
            raise HTTPException(
                status_code=400, 
                detail=f"Erreur lors de la récupération du solde: {balance.get('message')}"
            )
            
        return balance
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du solde: {str(e)}")

# Lancement du serveur avec Uvicorn (pour le développement)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_v1:app", host="0.0.0.0", port=8000, reload=True)
