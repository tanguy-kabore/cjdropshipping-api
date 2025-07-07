"""
Adaptateurs pour la transition de Pydantic v1 vers Pydantic v2
Ce fichier contient des fonctions et classes utilitaires pour faciliter
la migration de code utilisant Pydantic v1 vers Pydantic v2
"""

from typing import Any, Dict, Type, TypeVar, Optional, get_type_hints
from pydantic import BaseModel, Field, create_model

# Type générique pour les modèles Pydantic
ModelType = TypeVar('ModelType', bound=BaseModel)

def convert_schema_extra_to_json_schema_extra(cls: Type[BaseModel]) -> None:
    """
    Convertit les Config.schema_extra en model_config['json_schema_extra']
    pour la compatibilité avec Pydantic v2
    """
    if hasattr(cls, 'Config') and hasattr(cls.Config, 'schema_extra'):
        schema_extra = getattr(cls.Config, 'schema_extra')
        if not hasattr(cls, 'model_config'):
            setattr(cls, 'model_config', {})
        cls.model_config['json_schema_extra'] = schema_extra
        
def update_config_to_model_config(cls: Type[BaseModel]) -> None:
    """
    Convertit les anciennes configurations de classe Config en model_config
    pour la compatibilité avec Pydantic v2
    """
    if hasattr(cls, 'Config'):
        config = cls.Config
        model_config = {}
        
        # Mappages des attributs de Config vers model_config
        mappings = {
            'extra': 'extra',
            'allow_population_by_field_name': 'populate_by_name',
            'allow_mutation': 'frozen',  # Inverser la valeur
            'orm_mode': 'from_attributes',
            'validate_assignment': 'validate_assignment',
            'arbitrary_types_allowed': 'arbitrary_types_allowed',
            'use_enum_values': 'use_enum_values'
        }
        
        for old_attr, new_attr in mappings.items():
            if hasattr(config, old_attr):
                value = getattr(config, old_attr)
                # Cas spécial pour allow_mutation (inversé dans v2)
                if old_attr == 'allow_mutation':
                    value = not value
                model_config[new_attr] = value
        
        # Application des modifications
        if hasattr(cls, 'model_config'):
            cls.model_config.update(model_config)
        else:
            cls.model_config = model_config

def update_field_validators(cls: Type[BaseModel]) -> None:
    """
    Migration des anciens validators (v1) vers field_validators (v2)
    Cette fonction est un squelette, car la migration des validateurs
    nécessite une analyse plus approfondie du code
    """
    # Cette fonction sert principalement de rappel pour vérifier manuellement
    # les validateurs dans le code
    pass

def setup_fastapi_with_pydantic_v2():
    """
    Configure FastAPI pour utiliser correctement Pydantic v2
    """
    # Pas besoin de code particulier, FastAPI est compatible avec Pydantic v2
    # Cette fonction sert de documentation et de point d'extension futur
    pass

def adapt_pydantic_models(models: list[Type[BaseModel]]) -> None:
    """
    Adapte une liste de modèles Pydantic v1 pour qu'ils fonctionnent avec Pydantic v2
    """
    for model in models:
        convert_schema_extra_to_json_schema_extra(model)
        update_config_to_model_config(model)
