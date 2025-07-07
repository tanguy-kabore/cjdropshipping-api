import typing
from typing import ForwardRef

print("[INFO] Vérification de la compatibilité Pydantic avec Python 3.12+")

# Fonction de patch pour ForwardRef._evaluate
def _patched_evaluate(self, globalns=None, localns=None, recursive_guard=None):
    if recursive_guard is None:
        recursive_guard = set()
    return self._evaluate(globalns, localns, recursive_guard)

# Vérifie si la méthode nécessite un patch
try:
    # Obtient la signature de la méthode _evaluate
    import inspect
    signature = inspect.signature(ForwardRef._evaluate)
    
    # Si la méthode a déjà le paramètre recursive_guard, on applique le patch
    if 'recursive_guard' in signature.parameters:
        original_evaluate = ForwardRef._evaluate
        
        # Vérifie si la méthode a déjà été patchée
        if hasattr(original_evaluate, '_patched'):
            print("[INFO] Le patch Pydantic est déjà appliqué")
        else:
            # Applique le patch
            ForwardRef._evaluate = _patched_evaluate
            ForwardRef._evaluate._patched = True
            print("[OK] Patch Pydantic pour Python 3.12+ appliqué avec succès")
    else:
        print("[INFO] Patch Pydantic non nécessaire - version Python compatible")
except Exception as e:
    print(f"[WARNING] Impossible de vérifier la nécessité du patch Pydantic: {e}")
