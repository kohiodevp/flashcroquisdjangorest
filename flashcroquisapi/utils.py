from datetime import datetime
from rest_framework.response import Response

def standard_response(success, data=None, message=None, error=None, status_code=200, metadata=None):
    """Format de réponse standardisé avec métadonnées enrichies"""
    response_data = {
        'success': success,
        'timestamp': datetime.now().isoformat(),
        'data': data,
        'message': message,
        'error': error,
        'metadata': metadata or {}
    }
    return Response(response_data, status=status_code)

def handle_exception(e, context, message):
    """Gestion centralisée des exceptions"""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Erreur dans {context}: {e}")
    return standard_response(
        success=False,
        error={
            "type": type(e).__name__,
            "message": str(e),
            "context": context
        },
        message=message,
        status_code=500
    )

def format_layer_info(layer):
    """Formater les informations d'une couche de manière détaillée"""
    base_info = {
        'id': layer.id(),
        'name': layer.name(),
        'source': layer.source() if hasattr(layer, 'source') else None,
        'crs': layer.crs().authid() if hasattr(layer, 'crs') and layer.crs().isValid() else None
    }
    
    # Type de couche
    if hasattr(layer, 'type'):
        layer_type = layer.type()
        if layer_type == 0:  # Vector layer
            base_info['type'] = 'vector'
        elif layer_type == 1:  # Raster layer
            base_info['type'] = 'raster'
        else:
            base_info['type'] = 'unknown'
    
    # Calculer l'étendue de manière sûre
    try:
        extent = layer.extent()
        if extent and not extent.isEmpty():
            base_info['extent'] = {
                'xmin': round(extent.xMinimum(), 6),
                'ymin': round(extent.yMinimum(), 6),
                'xmax': round(extent.xMaximum(), 6),
                'ymax': round(extent.yMaximum(), 6),
            }
    except Exception as e:
        logger.warning(f"Erreur lors du calcul de l'étendue de la couche {layer.id()}: {e}")
    
    # Informations spécifiques aux couches vectorielles
    if hasattr(layer, 'featureCount'):
        try:
            base_info['feature_count'] = layer.featureCount()
        except Exception:
            base_info['feature_count'] = 0
    
    # Informations spécifiques aux couches raster
    if hasattr(layer, 'width') and hasattr(layer, 'height'):
        try:
            base_info['width'] = layer.width()
            base_info['height'] = layer.height()
            if hasattr(layer, 'dataProvider') and layer.dataProvider():
                base_info['bands'] = layer.dataProvider().bandCount()
        except Exception:
            base_info['width'] = 0
            base_info['height'] = 0
            base_info['bands'] = 0
    
    # Type de géométrie pour les couches vectorielles
    if hasattr(layer, 'geometryType'):
        try:
            geom_type = layer.geometryType()
            if geom_type == 0:
                base_info['geometry_type'] = 'point'
            elif geom_type == 1:
                base_info['geometry_type'] = 'line'
            elif geom_type == 2:
                base_info['geometry_type'] = 'polygon'
            else:
                base_info['geometry_type'] = 'unknown'
        except Exception:
            base_info['geometry_type'] = 'unknown'
    
    return base_info

def format_project_info(project):
    """Formater les informations d'un projet de manière détaillée"""
    layers_info = []
    for layer_id, layer in project.mapLayers().items():
        layers_info.append(format_layer_info(layer))
    
    return {
        'title': project.title(),
        'file_name': project.fileName(),
        'crs': project.crs().authid() if project.crs() else None,
        'layers': layers_info,
        'layers_count': len(layers_info),
        'created_at': project.createdAt() if hasattr(project, 'createdAt') else None,
        'last_modified': project.lastModified() if hasattr(project, 'lastModified') else None
    }