"""
json_utils.py - Utilidades JSON para Martyr v6.0

Funciones para manejar serialización JSON con tipos NumPy y otros tipos no nativos.
"""

import json
from pathlib import Path


def to_python_types(obj):
    """
    Convierte objetos NumPy y otros tipos no serializables a tipos Python nativos.
    
    Soluciona el error común: "Object of type bool_ is not JSON serializable"
    
    Parameters
    ----------
    obj : any
        Objeto a convertir (puede ser dict, list, numpy types, etc.)
    
    Returns
    -------
    any
        Objeto con tipos Python nativos
    
    Examples
    --------
    >>> import numpy as np
    >>> data = {'flag': np.bool_(True), 'count': np.int64(42)}
    >>> to_python_types(data)
    {'flag': True, 'count': 42}
    """
    # Importar numpy si está disponible
    try:
        import numpy as np
        HAS_NUMPY = True
    except ImportError:
        HAS_NUMPY = False
    
    if HAS_NUMPY:
        # Tipos NumPy a convertir
        if isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
    
    # Recursión para contenedores
    if isinstance(obj, dict):
        return {k: to_python_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_python_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(to_python_types(item) for item in obj)
    
    # Tipos nativos no requieren conversión
    return obj


def save_json_safe(data, filepath, indent=2, ensure_ascii=False):
    """
    Guarda datos JSON de forma segura, convirtiendo tipos no serializables.
    
    Parameters
    ----------
    data : any
        Datos a guardar
    filepath : str o Path
        Ruta del archivo de salida
    indent : int
        Indentación para formato pretty-print
    ensure_ascii : bool
        Si False, permite caracteres UTF-8
    
    Returns
    -------
    Path
        Ruta del archivo guardado
    """
    # Convertir tipos no serializables
    safe_data = to_python_types(data)
    
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(safe_data, f, indent=indent, ensure_ascii=ensure_ascii)
    
    return filepath


def load_json_safe(filepath):
    """
    Carga JSON de forma segura.
    
    Parameters
    ----------
    filepath : str o Path
        Ruta del archivo JSON
    
    Returns
    -------
    dict o list
        Datos del JSON
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)
