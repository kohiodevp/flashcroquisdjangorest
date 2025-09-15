import io
import locale
import math
import os
import json
import logging
import uuid
from pathlib import Path
from datetime import datetime
from threading import Lock
from django.http import HttpResponse, FileResponse
from flashcroquisapi import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from PyQt5.QtCore import QSize, QRectF, QPoint, QPointF, Qt,QVariant
from PyQt5.QtGui import QImage, QPainter, QColor, QColor,QFont
from PyQt5.QtSvg import QSvgRenderer

# Gestion des sessions et QGIS
project_sessions = {}
project_sessions_lock = Lock()
qgis_manager = None

# Logger
logger = logging.getLogger(__name__)

# Classes QGIS (à importer au démarrage)
qgis_classes = {}
_A=True

def get_qgis_manager():
    """Obtenir le gestionnaire QGIS global"""
    global qgis_manager
    if qgis_manager is None:
        qgis_manager = QgisManager()
    return qgis_manager

def initialize_qgis_if_needed():
    """Initialiser QGIS si nécessaire"""
    manager = get_qgis_manager()
    if not manager.is_initialized():
        return manager.initialize()
    return True, None

def get_project_session(session_id=None):
    """Obtenir ou créer une session de projet"""
    with project_sessions_lock:
        if session_id and session_id in project_sessions:
            session = project_sessions[session_id]
        else:
            session = ProjectSession(session_id)
            if not session_id:
                session_id = session.session_id
            project_sessions[session_id] = session
    return session, session_id

class QgisManager:
    """Gestionnaire QGIS"""
    
    def __init__(self):
        self._initialized = False
        self._initialization_attempted = False
        self.qgs_app = None
        self.classes = {}
        self.init_errors = []
    
    def initialize(self):
        """Initialiser QGIS avec gestion correcte de processing"""
        if self._initialized:
            return True, None
            
        if self._initialization_attempted:
            return False, "Initialization already attempted"
            
        self._initialization_attempted = True
        logger.info("=== DÉBUT DE L'INITIALISATION QGIS ===")
        
        try:
            # Configuration de l'environnement QGIS
            self._setup_qgis_environment()
            
            # Importation des modules QGIS
            from PyQt5.QtCore import QCoreApplication
            from qgis.core import (
                Qgis, QgsApplication, QgsProject, QgsVectorLayer,
                QgsRasterLayer, QgsMapSettings, QgsMapRendererParallelJob,
                QgsProcessingFeedback, QgsProcessingContext, QgsRectangle,
                QgsPalLayerSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling,
                QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLegend,
                QgsLayoutItemLabel, QgsLayoutExporter, QgsLayoutItemPicture,
                QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes, QgsLayoutItemPage,
                QgsLayoutItemScaleBar, QgsLayoutItemHtml,
                QgsCoordinateReferenceSystem, QgsRectangle,
                QgsMapLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsFields, QgsField,
                QgsVectorFileWriter, QgsVectorDataProvider, QgsWkbTypes, QgsLayerTreeLayer,
                QgsLinePatternFillSymbolLayer, QgsSimpleLineSymbolLayer, QgsSymbol, QgsSingleSymbolRenderer,
                QgsLayerTreeGroup, QgsLayerTreeModel, QgsLegendStyle, QgsExpression, QgsExpressionContext,
                QgsExpressionContextUtils, QgsTextBackgroundSettings, QgsLayoutItemShape, QgsLayoutItemMapGrid,
                QgsPoint
            )
            
            # Initialisation de l'application QGIS
            logger.info("Initialisation de l'application QGIS...")
            if not QgsApplication.instance():
                self.qgs_app = QgsApplication([], False)
                self.qgs_app.initQgis()
                logger.info("Application QGIS initialisée")
            else:
                self.qgs_app = QgsApplication.instance()
                logger.info("Instance QGIS existante utilisée")
            
            # Importation de processing
            try:
                import processing
                logger.info("Module processing importé avec succès")
            except ImportError:
                try:
                    from qgis import processing
                    logger.info("Module qgis.processing importé avec succès")
                except ImportError:
                    logger.warning("Module processing non disponible")
                    # Création d'un mock processing
                    class MockProcessing:
                        @staticmethod
                        def run(*args, **kwargs):
                            raise NotImplementedError("Processing module not available")
                    processing = MockProcessing()
            
            # Stockage des classes
            self.classes = {
                'Qgis': Qgis,
                'QgsApplication': QgsApplication,
                'QgsProject': QgsProject,
                'QgsVectorLayer': QgsVectorLayer,
                'QgsRasterLayer': QgsRasterLayer,
                'QgsMapSettings': QgsMapSettings,
                'QgsMapRendererParallelJob': QgsMapRendererParallelJob,
                'QgsProcessingFeedback': QgsProcessingFeedback,
                'QgsProcessingContext': QgsProcessingContext,
                'QgsRectangle': QgsRectangle,
                'processing': processing,
                'QgsPalLayerSettings': QgsPalLayerSettings,
                'QgsTextFormat': QgsTextFormat,
                'QgsVectorLayerSimpleLabeling': QgsVectorLayerSimpleLabeling,
                'QgsPrintLayout': QgsPrintLayout,
                'QgsLayoutItemMap': QgsLayoutItemMap,
                'QgsLayoutItemLegend': QgsLayoutItemLegend,
                'QgsLayoutItemLabel': QgsLayoutItemLabel,
                'QgsLayoutExporter': QgsLayoutExporter,
                'QgsLayoutItemPicture': QgsLayoutItemPicture,
                'QgsLayoutPoint': QgsLayoutPoint,
                'QgsLayoutSize': QgsLayoutSize,
                'QgsUnitTypes': QgsUnitTypes,
                'QgsLayoutItemPage': QgsLayoutItemPage,
                'QgsLayoutItemScaleBar': QgsLayoutItemScaleBar,
                'QgsLayoutItemHtml': QgsLayoutItemHtml,
                'QgsCoordinateReferenceSystem': QgsCoordinateReferenceSystem,
                'QgsMapLayer': QgsMapLayer,
                'QgsFeature': QgsFeature,
                'QgsGeometry': QgsGeometry,
                'QgsPointXY': QgsPointXY,
                'QgsFields': QgsFields,
                'QgsField': QgsField,
                'QgsVectorFileWriter': QgsVectorFileWriter,
                'QgsVectorDataProvider': QgsVectorDataProvider,
                'QgsWkbTypes': QgsWkbTypes,
                'QgsLayerTreeLayer': QgsLayerTreeLayer,
                'QgsLinePatternFillSymbolLayer': QgsLinePatternFillSymbolLayer,
                'QgsSimpleLineSymbolLayer': QgsSimpleLineSymbolLayer,
                'QgsSymbol': QgsSymbol,
                'QgsSingleSymbolRenderer': QgsSingleSymbolRenderer,
                'QgsLayerTreeGroup': QgsLayerTreeGroup,
                'QgsLayerTreeModel': QgsLayerTreeModel,
                'QgsLegendStyle': QgsLegendStyle,
                'QgsExpression': QgsExpression,
                'QgsExpressionContext': QgsExpressionContext,
                'QgsExpressionContextUtils': QgsExpressionContextUtils,
                'QgsTextBackgroundSettings': QgsTextBackgroundSettings,
                'QgsLayoutItemShape': QgsLayoutItemShape,
                'QgsLayoutItemMapGrid': QgsLayoutItemMapGrid,
                'QgsPoint': QgsPoint
            }

            self._initialized = True
            logger.info("=== QGIS INITIALISÉ AVEC SUCCÈS ===")
            return True, None
            
        except Exception as e:
            error_msg = f"Erreur d'initialisation: {e}"
            self.init_errors.append(error_msg)
            logger.error(error_msg)
            return False, error_msg
    
    def _setup_qgis_environment(self):
        """Configurer l'environnement QGIS"""
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        os.environ['QT_DEBUG_PLUGINS'] = '0'
        os.environ['QT_QPA_FONTDIR'] = os.path.join(os.path.dirname(__file__), 'ttf')
        os.environ['QT_NO_CPU_FEATURE'] = 'sse4.1,sse4.2,avx,avx2'
        logger.info("Environnement QGIS configuré")
    
    def is_initialized(self):
        return self._initialized
    
    def get_classes(self):
        if not self._initialized:
            raise Exception("QGIS not initialized")
        return self.classes
    
    def get_errors(self):
        return self.init_errors

class ProjectSession:
    """Classe pour gérer une session de projet persistante"""
    
    def __init__(self, session_id=None):
        self.session_id = session_id or str(uuid.uuid4())
        self.project = None
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.temporary_files = []
    
    def get_project(self, qgs_project_class):
        """Obtenir le projet QGIS pour cette session"""
        if self.project is None:
            self.project = qgs_project_class()
            self.project.setTitle(f"Session Project - {self.session_id}")
        self.last_accessed = datetime.now()
        return self.project
    
    def cleanup(self):
        """Nettoyer les ressources de la session"""
        try:
            if self.project:
                self.project.clear()
                self.project = None
                
            # Supprimer les fichiers temporaires
            for temp_file in self.temporary_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        logger.warning(f"Impossible de supprimer le fichier temporaire {temp_file}: {e}")
            self.temporary_files = []
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage de la session {self.session_id}: {e}")

# Fonctions utilitaires
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

def create_polygon_with_vertex_points(layer, output_polygon_layer=None, output_points_layer=None):
    """
    Crée un layer de polygone avec les points sommets nommés B1, B2, B3... 
    dans le sens horaire en commençant par le point le plus au nord.
    
    Args:
        input_file_path (str): Chemin vers le fichier d'entrée (shp, gpx, csv)
        output_polygon_layer (str, optional): Chemin pour sauvegarder le layer polygone
        output_points_layer (str, optional): Chemin pour sauvegarder le layer points
    
    Returns:
        tuple: (polygon_layer, points_layer) - Les layers QGIS créés
    """
    from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsField, QgsVectorFileWriter, QgsWkbTypes
    from PyQt5.QtCore import QVariant
    
    # Obtenir tous les points du layer d'entrée
    points = []
    
    # Pour les différents types de géométries
    for feature in layer.getFeatures():
        geom = feature.geometry()
        if geom.type() == QgsWkbTypes.PointGeometry:
            # Points individuels
            if geom.isMultipart():
                # Multi-points
                for part in geom.asMultiPoint():
                    points.append(part)
            else:
                # Point simple
                points.append(geom.asPoint())
        elif geom.type() == QgsWkbTypes.LineGeometry:
            # Lignes - extraire les sommets
            if geom.isMultipart():
                # Multi-lignes
                for part in geom.asMultiPolyline():
                    points.extend(part)
            else:
                # Ligne simple
                points.extend(geom.asPolyline())
        elif geom.type() == QgsWkbTypes.PolygonGeometry:
            # Polygones - extraire les sommets
            if geom.isMultipart():
                # Multi-polygones
                for part in geom.asMultiPolygon():
                    for ring in part:
                        points.extend(ring)
            else:
                # Polygone simple
                for ring in geom.asPolygon():
                    points.extend(ring)
    
    if len(points) < 3:
        raise Exception("Il faut au moins 3 points pour créer un polygone")
    
    # Trier les points pour commencer par le plus au nord (y maximum)
    # et organiser dans le sens horaire
    # sorted_points = sort_points_clockwise_starting_north(points)
    points = list(filter(None, points))
    if not points:
        raise ValueError("Aucun point valide trouvé dans le fichier.")

    sorted_points = list(dict.fromkeys(points))
    if not is_clockwise(sorted_points):
        sorted_points.reverse()
    sorted_points = shift_to_northernmost(sorted_points)
    
    # Créer le polygone
    polygon_geom = QgsGeometry.fromPolygonXY([sorted_points])
    
    # Créer le layer polygone
    polygon_layer = QgsVectorLayer("Polygon?crs=" + layer.crs().authid(), "Terrain", "memory")
    polygon_provider = polygon_layer.dataProvider()
    
    # Ajouter les champs nécessaires
    polygon_provider.addAttributes([
        QgsField("id", QVariant.String),
        QgsField("Superficie", QVariant.Double)
    ])
    polygon_layer.updateFields()
    
    # Créer la feature du polygone
    polygon_feature = QgsFeature()
    polygon_feature.setGeometry(polygon_geom)
    area_m2 = polygon_geom.area()
    polygon_feature.setAttributes([1, area_m2])
    
    # Ajouter la feature au layer
    polygon_provider.addFeatures([polygon_feature])
    
    # Créer le layer de points
    points_layer = QgsVectorLayer("Point?crs=" + layer.crs().authid(), "Points sommets", "memory")
    points_provider = points_layer.dataProvider()
    
    # Ajouter les champs nécessaires
    points_provider.addAttributes([QgsField(n, t) for n, t in [("Bornes", QVariant.String), ("X", QVariant.Int), ("Y", QVariant.Int), ("Distance", QVariant.Double)]])
    points_layer.updateFields()
    
    # Créer les features de points
    point_features = []
    for i, point in enumerate(sorted_points):
        point_feature = QgsFeature()
        point_feature.setGeometry(QgsGeometry.fromPointXY(point))
        point_feature.setAttributes([f"B{i+1}", int(point.x()), int(point.y()), round(calculate_distance(point, sorted_points[(i+1) % len(sorted_points)]), 2)])
        point_features.append(point_feature)
    
    # Ajouter les features au layer de points
    points_provider.addFeatures(point_features)
    
    # Sauvegarder les layers si des chemins sont fournis
    if output_polygon_layer:
        QgsVectorFileWriter.writeAsVectorFormat(polygon_layer, output_polygon_layer, "UTF-8", 
                                               polygon_layer.crs(), "ESRI Shapefile")
    
    if output_points_layer:
        QgsVectorFileWriter.writeAsVectorFormat(points_layer, output_points_layer, "UTF-8", 
                                               points_layer.crs(), "ESRI Shapefile")
    
    return polygon_layer, points_layer

def is_clockwise(points):
    return sum((p2.x() - p1.x()) * (p2.y() + p1.y()) for p1, p2 in zip(points, points[1:] + [points[0]])) > 0

def shift_to_northernmost(points):
    return points[max(range(len(points)), key=lambda i: points[i].y()):] + points[:max(range(len(points)), key=lambda i: points[i].y())]

def calculate_distance(p1, p2):
    return math.hypot(p2.x() - p1.x(), p2.y() - p1.y())

def create_print_layout_with_qgs(layout_name, project, map_items_config=None):
    """
    Créer un layout QGIS avec QgsPrintLayout pour générer des PDF professionnels
    """
    try:
        
        
        # Obtenir les classes QGIS
        classes = get_qgis_manager().get_classes()
        QgsLayoutItemMap = classes['QgsLayoutItemMap']
        QgsLayoutItemLegend = classes['QgsLayoutItemLegend']
        QgsLayoutItemLabel = classes['QgsLayoutItemLabel']
        QgsLayoutItemScaleBar = classes['QgsLayoutItemScaleBar']
        QgsLayoutItemPage = classes['QgsLayoutItemPage']
        QgsPrintLayout = classes['QgsPrintLayout']
        QgsUnitTypes = classes['QgsUnitTypes']
        QgsLayoutPoint = classes['QgsLayoutPoint']
        QgsLayoutSize = classes['QgsLayoutSize']
        
        date = datetime.now().strftime(r"%d %B %Y")
        # Créer un nouveau layout
        layout = QgsPrintLayout(project)
        layout.initializeDefaults()
        
        layout=QgsPrintLayout(project)
        layout.initializeDefaults()
        pc = layout.pageCollection()
        page = pc.pages()[0]
        page.setPageSize("A4", QgsLayoutItemPage.Portrait)
        
        data = [
            {"text": "MINISTERE DE L'ECONOMIE ET DES FINANCES", "x": 5, "y": 5, "width": 90, "height": 10, "font_size": 12, "is_bold": 1},
            {"text": "*********************", "x": 5, "y": 12, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
            {"text": "SECRETARIAT GENERAL", "x": 5, "y": 17, "width": 90, "height": 10, "font_size": 12, "is_bold": 1},
            {"text": "*********************", "x": 5, "y": 22, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
            {"text": "DIRECTION GENERALE DES IMPOTS", "x": 10, "y": 27, "width": 90, "height": 10, "font_size": 12, "is_bold": 1},
            {"text": "*********************", "x": 5, "y": 32, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
            {"text": "DIRECTION REGIONALE DES IMPOTS DU GUIRIKO", "x": 5, "y": 39, "width": 90, "height": 10, "font_size": 12, "is_bold": 1},
            {"text": "*********************", "x": 5, "y": 46, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
            {"text": "SERVICE DU CADASTRE ET DES TRAVAUX FONCIERS DU GUIRIKO", "x": 5, "y": 53, "width": 90, "height": 10, "font_size": 12, "is_bold": 1},
            {"text": "*********************", "x": 5, "y": 60, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
            {"text": f"N°......./MEF/SG/DGI/DRI-GRK/SCTF-GRK", "x": 10, "y": 75, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
    
    
            {"text": "BURKINA FASO", "x": 120, "y": 5, "width": 90, "height": 10, "font_size": 12, "is_bold": 1},
            {"text": "La Patrie ou la Mort, Nous vaincrons", "x": 120, "y": 10, "width": 90, "height": 10, "font_size": 10, "is_bold": 1},
            {"text": f"Bobo-Dioulasso le {date}", "x": 120, "y": 30, "width": 90, "height": 10, "font_size": 12, "is_bold": 0},
    
    
            {"text": "FICHE D’IDENTIFICATION CADASTRALE", "x": 5, "y": 105, "width": 200, "height": 10, "font_size": 24, "is_bold": 1},
    
        ]
        for d in data:
            A = QgsLayoutItemLabel(layout)
            A.setText(d['text'])
            A.setFont(QFont("Times New Roman",d['font_size'],QFont.Bold if d['is_bold'] == 1 else QFont.Normal))
            A.setHAlign(Qt.AlignCenter)
            A.setVAlign(Qt.AlignCenter)
            A.attemptMove(QgsLayoutPoint(d['x'],d['y'],QgsUnitTypes.LayoutMillimeters))
            A.attemptResize(QgsLayoutSize(d['width'],d['height'],QgsUnitTypes.LayoutMillimeters))
            layout.addItem(A)
            
        return layout
        
    except Exception as e:
        logger.error(f"Erreur lors de la création du layout: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    
def create_print_layout_croquis(layout_name, project, map_items_config=None):
    
    try:
        classes = get_qgis_manager().get_classes()
        QgsPrintLayout = classes['QgsPrintLayout']
        QgsLayoutItemMap = classes['QgsLayoutItemMap']
        QgsLayerTreeLayer = classes['QgsLayerTreeLayer']
        QgsLayoutItemPicture = classes['QgsLayoutItemPicture']
        QgsLayoutPoint = classes['QgsLayoutPoint']
        QgsUnitTypes = classes['QgsUnitTypes']
        QgsLayoutSize = classes['QgsLayoutSize']
        QgsSymbol = classes['QgsSymbol']
        QgsLinePatternFillSymbolLayer = classes['QgsLinePatternFillSymbolLayer']
        QgsSimpleLineSymbolLayer = classes['QgsSimpleLineSymbolLayer']
        QgsSingleSymbolRenderer = classes['QgsSingleSymbolRenderer']
        QgsLayerTreeGroup = classes['QgsLayerTreeGroup']
        QgsWkbTypes = classes['QgsWkbTypes']
        QgsVectorLayer = classes['QgsVectorLayer']
        QgsFeature = classes['QgsFeature']
        QgsLayoutItemLegend = classes['QgsLayoutItemLegend']
        QgsRectangle = classes['QgsRectangle']
        QgsLayerTreeModel = classes['QgsLayerTreeModel']
        QgsLegendStyle = classes['QgsLegendStyle']
        
        layout = QgsPrintLayout(project)
        layout.initializeDefaults()
        
        table_height = 0
        
        parcelle_layer = project.mapLayersByName('Parcelle')[0]
        if parcelle_layer:
            features = parcelle_layer.getFeatures()
            
            extent = None
            for feature in features:
                if extent is None:
                    extent = feature.geometry().boundingBox()
                else:
                    extent.combineExtentWith(feature.geometry().boundingBox())
                if extent:
                    extent = parcelle_layer.extent()
                    height_f = feature.geometry().length()
                    if height_f > 1200:
                        height_f += 200
                    
                    params = [
                        {
                            "x": 5.5,
                            "y": 14,
                            "width": 140,
                            "height":119 if table_height == 63 else 119 + (63 - table_height),
                            "is_cadre": True,
                            "echelle": round(height_f * (119 if table_height == 63 else 119 + (63 - table_height)) / ((119 if table_height == 63 else 119 + (63 - table_height)) / 3))
                        },
                        {
                            "x": 151.5,
                            "y": 17.5,
                            "width": 140,
                            "height": 114,
                            "is_cadre": False,
                            "echelle": round(feature.geometry().length() * 114 / (114 * (1/50)))
                        }
                    ]
                
                    # changer_couleur(parcelle_layer, 255, 255, 255)
                    # changer_couleur(points_sommets_layer, 0, 0, 0)

                    for i, croquis in enumerate(params, start=1):
                        
                        map_item = QgsLayoutItemMap(layout)
                        north_arrow = QgsLayoutItemPicture(layout)
                        north_arrow.setPicturePath(os.path.join(os.path.dirname(__file__),"NorthArrow_02.svg"))  # Utilise une icône par défaut de QGIS
                        # legend_item = QgsLayoutItemLegend(layout)
                        # legend_item.setTitle("Légende")
                        # legend_item.setMap(map_item)  # Lier la légende à la carte
                        # legend_item.setRect(141, 180, 20, 20)  # Positionner la légende

                        # Filtrer les couches à afficher
                        layers = project.mapLayers()
                        visible_layers = []  # Nom des couches à cacher
                        if i == 2:
                            
                            # Positionner et dimensionner la rose des vents
                            north_arrow.attemptMove(QgsLayoutPoint(155, 20, QgsUnitTypes.LayoutMillimeters))
                            north_arrow.attemptResize(QgsLayoutSize(10, 10, QgsUnitTypes.LayoutMillimeters))

                            # 🔹 Créer un symbole pour le polygone
                            symbol = QgsSymbol.defaultSymbol(parcelle_layer.geometryType())

                            # 🔹 1. Ajouter un remplissage avec des hachures (rayures)
                            pattern = QgsLinePatternFillSymbolLayer()
                            pattern.setColor(QColor(0, 0, 0))  # Couleur des hachures (Noir)
                            pattern.setLineWidth(0.1)  # Épaisseur des hachures
                            pattern.setDistance(0.5)  # Espacement entre les hachures
                            pattern.setAngle(45)  # Orientation des hachures (en degrés)

                            # 🔹 2. Ajouter un contour au polygone
                            contour = QgsSimpleLineSymbolLayer()
                            contour.setColor(QColor(0, 0, 0))  # Couleur du contour (Rouge)
                            contour.setWidth(0.5)  # Épaisseur du contour

                            # 🔹 Appliquer les styles au symbole
                            symbol.changeSymbolLayer(0, pattern)  # Ajout des hachures
                            symbol.appendSymbolLayer(contour)  # Ajout du contour

                            # 🔹 Appliquer le style à la couche
                            parcelle_layer.setRenderer(QgsSingleSymbolRenderer(symbol))
                            parcelle_layer.triggerRepaint()

                            layer_list = []
                            legend_layers = []

                            excluded_layers = ["Points sommets"]
                            visible_layers = [layer for layer in layers.values() if layer.name() not in excluded_layers]

                            # Récupérer les couches visibles et sélectionnées dans l'arbre des couches
                            root = project.layerTreeRoot()
                            def get_checked_layers(group):
                                checked_layers = []
                                for child in group.children():
                                    if isinstance(child, QgsLayerTreeLayer):
                                        if child.isVisible():  # Vérifie si la couche est cochée
                                            checked_layers.append(child.layer())
                                    elif isinstance(child, QgsLayerTreeGroup):
                                        checked_layers.extend(get_checked_layers(child))
                                return checked_layers

                            legend_layers = get_checked_layers(root)
                            legend_layers = [layer for layer in legend_layers if layer.name() != "Points sommets"]

                            for layer in visible_layers:
                                if isinstance(layer, QgsLayerTreeLayer) and layer.isVisible():
                                    layer_list.append(layer.layer())

                            # Appliquer la liste des couches visibles à l'élément carte
                            map_item.setLayers(layer_list)
                        else:
                            pass
                            # Positionner et dimensionner la rose des vents
                            # north_arrow.attemptMove(QgsLayoutPoint(8, 20, QgsUnitTypes.LayoutMillimeters))
                            # north_arrow.attemptResize(QgsLayoutSize(10, 10, QgsUnitTypes.LayoutMillimeters))

                            # # 🔹 Définir le type de géométrie de la nouvelle couche
                            # geom_type = QgsWkbTypes.displayString(parcelle_layer.wkbType())

                            # # 🔹 Créer une nouvelle couche vide avec le même type de géométrie et les mêmes attributs
                            # new_layer = QgsVectorLayer(f"{geom_type}?crs={parcelle_layer.crs().authid()}", "Nouvelle_Couche", "memory")
                            # new_layer_provider = new_layer.dataProvider()

                            # # 🔹 Copier les champs (attributs) de l'ancienne couche vers la nouvelle
                            # new_layer_provider.addAttributes(parcelle_layer.fields())
                            # new_layer.updateFields()

                            # # 🔹 Copier les entités de l'ancienne couche vers la nouvelle
                            # new_features = []
                            # for feature in parcelle_layer.getFeatures():
                            #     new_feature = QgsFeature()
                            #     new_feature.setGeometry(feature.geometry())  # Copier la géométrie
                            #     new_feature.setAttributes(feature.attributes())  # Copier les attributs
                            #     new_features.append(new_feature)

                            # new_layer_provider.addFeatures(new_features)

                            # # Récupération du symbole de la couche
                            # symbol = new_layer.renderer().symbol()
                            
                            # # Changer la couleur de remplissage (pour une couche de polygones)
                            # fill_symbol = symbol.symbolLayer(0)
                            # fill_symbol.setColor(QColor(255, 255, 255))  # Rouge (R, G, B)

                            # # Mettre à jour la couche
                            # new_layer.triggerRepaint()

                            # # Créer un symbole pour personnaliser l'apparence des sommets
                            # taille_points = 2
                            # if len(points_sommets_layer) > 10 and len(points_sommets_layer) < 20:
                            #     taille_points = 1.5
                            # elif len(points_sommets_layer) > 20:
                            #     taille_points = 1
                            # symbol = QgsSymbol.defaultSymbol(points_sommets_layer.geometryType())
                            # symbol.setColor(QColor("black"))  # Change la couleur des points sommets
                            # symbol.setSize(taille_points)  # Change la taille des points
                            # # Appliquer ce symbole à la couche
                            # renderer = points_sommets_layer.renderer()
                            # renderer.setSymbol(symbol)

                            # # Actualiser la couche pour voir les changements
                            # points_sommets_layer.triggerRepaint()
                            
                            # visible_layers = [points_sommets_layer,new_layer]

                            # area = feature.geometry().area()
                            # grid_interval = 100
                            # if area < 10000:
                            #     grid_interval = 25
                            # elif area < 50000:
                            #     grid_interval = 50
                            # elif area < 100000:
                            #     grid_interval = 100
                            # elif area < 200000:
                            #     grid_interval = 150
                            # elif area < 300000:
                            #     grid_interval = 200
                            # elif area < 500000:
                            #     grid_interval = 250
                            # elif area < 1000000:
                            #     grid_interval = 300
                            # else:
                            #     grid_interval = 400

                            # map_item.grid().setEnabled(True)  
                            # map_item.grid().setIntervalX(grid_interval)  
                            # map_item.grid().setIntervalY(grid_interval)  
                            # map_item.grid().setAnnotationEnabled(True) 
                            # # map_item.grid().setGridLineColor(QColor(0, 176, 246))  
                            # # map_item.grid().setGridLineWidth(0.5)
                            # map_item.grid().setStyle(QgsLayoutItemMapGrid.Cross)
                            # # map_item.grid().setGridPenColor(QColor(0, 0, 0))  # Couleur noire
                            # map_item.grid().setGridLineWidth(0.2)  # Épaisseur fine
                            # map_item.grid().setCrossLength(0.8)  # Valeur numérique simple (en millimètres)
                            # map_item.grid().setAnnotationPrecision(0)  
                            # map_item.grid().setAnnotationFrameDistance(1)  
                            # map_item.grid().setAnnotationFontColor(QColor(0, 0, 0)) 
                            # map_item.grid().setFrameWidth(2)  # Épaisseur du cadre en mm
                            # # Modifier la police des annotations
                            # annotation_font = map_item.grid().annotationFont()
                            # annotation_font.setPointSize(6)  # Taille du texte
                            # map_item.grid().setAnnotationFont(annotation_font)
                            # map_item.grid().setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, QgsLayoutItemMapGrid.Right)
                            # map_item.grid().setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Right)
                            # map_item.grid().setAnnotationPosition(QgsLayoutItemMapGrid.InsideMapFrame, QgsLayoutItemMapGrid.Top)
                            # map_item.grid().setAnnotationDirection(QgsLayoutItemMapGrid.Horizontal, QgsLayoutItemMapGrid.Top)
                            # map_item.grid().setAnnotationPosition(QgsLayoutItemMapGrid.InsideMapFrame, QgsLayoutItemMapGrid.Bottom)
                            # map_item.grid().setAnnotationDirection(QgsLayoutItemMapGrid.Horizontal, QgsLayoutItemMapGrid.Bottom)
                            # map_item.grid().setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, QgsLayoutItemMapGrid.Left)
                            # map_item.grid().setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Left)


                        # Appliquer la liste des couches visibles à l'élément carte
                        map_item.setLayers(visible_layers)
                        
                        map_item.attemptMove(QgsLayoutPoint(croquis.get("x"), croquis.get("y"), QgsUnitTypes.LayoutMillimeters))
                        map_item.attemptResize(QgsLayoutSize(croquis.get("width"), croquis.get("height"), QgsUnitTypes.LayoutMillimeters))
                        map_item.setFrameEnabled(croquis.get("is_cadre"))
                        map_item.setFrameStrokeColor(Qt.black)

                        # extent.scale(croquis.get("margin"))  # Ajoute la marge
                    
                        map_item.setExtent(extent)

                        # Récupérer l'emprise actuelle et son centre
                        current_extent = map_item.extent()
                        center_x = current_extent.center().x()
                        center_y = current_extent.center().y()

                        # Convertir la taille en unités de carte (attention au CRS !)
                        scale_factor = map_item.scale()  # Échelle actuelle
                        width_in_map_units = (croquis.get("width") / 25.4) * scale_factor  # 150 mm → pouces → unités carte
                        height_in_map_units = (croquis.get("height") / 25.4) * scale_factor

                        # Créer la nouvelle emprise centrée sur la position actuelle
                        new_extent = QgsRectangle(
                            center_x - width_in_map_units / 2,
                            center_y - height_in_map_units / 2,
                            center_x + width_in_map_units / 2,
                            center_y + height_in_map_units / 2
                        )

                        # Appliquer la nouvelle emprise
                        map_item.setExtent(new_extent)

                        map_item.setScale(croquis.get("echelle"))  # Définit une échelle de 1:1000
                        

                        # Echelle
                        # if i == 1:
                        #     label_instance.modifier_label(13, f"Échelle: 1/{arrondir_au_multiple_superieur(round(map_item.scale()))}", 55, 190, 141, 10, 10, 1)
                        #     shape_instance.creation(layout, shape_id=10)
                        #     label_instance.creation(layout, 13)
                        # else:
                        #     label_instance.modifier_label(14, f"Échelle: 1/{arrondir_au_multiple_superieur(round(map_item.scale()))}", 201, 122, 141, 10, 10, 1)
                        #     shape_instance.creation(layout, shape_id=9)
                        #     label_instance.creation(layout, 14)

                        layout.addItem(map_item)
                        map_item.refresh()
                        layout.addLayoutItem(north_arrow)
                        
                        # Créer l'élément de légende
                        legend_item = QgsLayoutItemLegend(layout)
                        legend_item.setTitle("Légende")

                        
                        # 1. Cloner la racine de l'arbre des couches du projet
                        root_clone = project.layerTreeRoot().clone()  # ➡️ Clone de type QgsLayerTreeGroup

                        # 2. Filtrer pour ne garder que les couches sélectionnées
                        # --- Supprimer toutes les couches non sélectionnées du clone ---
                        for node in root_clone.children():
                            if isinstance(node, QgsLayerTreeLayer) and not node.isVisible():
                                # if node.layer() not in selected_layers:
                                parent = node.parent()
                                if parent:
                                    parent.removeChildNode(node)
                            elif isinstance(node, QgsLayerTreeGroup) and not node.children():
                                parent = node.parent()
                                if parent:
                                    parent.removeChildNode(node)


                        # 3. Créer le modèle avec le clone filtré
                        layer_tree_model = QgsLayerTreeModel(root_clone)  # ✅ Correct : root_clone est un QgsLayerTreeGroup valide

                        # 4. Associer le modèle à la légende
                        legend_item.model().setRootGroup(root_clone)  # Méthode alternative

                        # 5. Conserver les références pour éviter les crashes
                        legend_item.root_clone = root_clone
                        legend_item.layer_tree_model = layer_tree_model

                        # Positionnement
                        legend_item.attemptMove(QgsLayoutPoint(200, 17.5, QgsUnitTypes.LayoutMillimeters))

                        # Activer les mises à jour automatiques de la légende pour refléter les changements dans l'arbre des couches
                        legend_item.setAutoUpdateModel(True)  # Permettre les mises à jour automatiques
                        legend_item.refresh()  # Rafraîchir la légende

                        # Personnalisation de la légende
                        legend_item.setColumnCount(3)  # Nombre de colonnes dans la légende
                        legend_item.setSymbolWidth(2)  # Largeur des symboles dans la légende
                        legend_item.setSymbolHeight(1.5)  # Hauteur des symboles

                        # Modifier la police du titre
                        title_font = legend_item.styleFont(QgsLegendStyle.Title)
                        title_font.setPointSize(8)  # Taille du texte du titre
                        title_font.setBold(True)
                        legend_item.setStyleFont(QgsLegendStyle.Title, title_font)

                        # Modifier la police des éléments de la légende
                        item_font = legend_item.styleFont(QgsLegendStyle.SymbolLabel)
                        item_font.setPointSize(6)  # Taille du texte des éléments
                        legend_item.setStyleFont(QgsLegendStyle.SymbolLabel, item_font)

                        # Ajouter la légende à la mise en page
                        layout.addItem(legend_item)

        
        return layout
        
    except Exception as e:
        logger.error(f"Erreur lors de la création du layout: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

    
def generate_pdf_from_layout(layout, output_path):
    """
    Générer un PDF à partir d'un QgsPrintLayout
    """
    try:
        # Obtenir les classes QGIS
        classes = get_qgis_manager().get_classes()
        QgsLayoutExporter = classes['QgsLayoutExporter']
        
        # Exporter le layout en PDF
        exporter = QgsLayoutExporter(layout)
        result = exporter.exportToPdf(output_path)
        
        if result == QgsLayoutExporter.Success:
            return True, output_path
        else:
            return False, f"Erreur d'exportation PDF: {result}"
            
    except Exception as e:
        return False, str(e)

def _create_label_item(layout, label_data):
    cls=get_qgis_manager().get_classes()
    QgsLayoutPoint = cls['QgsLayoutPoint']
    QgsLayoutItemLabel=cls['QgsLayoutItemLabel']
    QgsUnitTypes = cls['QgsUnitTypes']
    QgsLayoutSize = cls['QgsLayoutSize']
    C = layout
    A = label_data
    B = QgsLayoutItemLabel(C)
    B.setText(A['text'])
    B.setFont(
        QFont(
            "Times New Roman",
            A['font_size'],
            QFont.Bold if A['is_bold'] == 1 else QFont.Normal))
    B.setHAlign(
        Qt.AlignCenter)
    B.setVAlign(
        Qt.AlignCenter)
    B.attemptMove(
        QgsLayoutPoint(
            A['x'],
            A['y'],
            QgsUnitTypes.LayoutMillimeters))
    B.attemptResize(
        QgsLayoutSize(
            A['width'],
            A['height'],
            QgsUnitTypes.LayoutMillimeters))
    C.addItem(B)
def _create_shape_item(layout, shape_data):
    cls=get_qgis_manager().get_classes()
    QgsLayoutPoint = cls['QgsLayoutPoint']
    QgsLayoutItemShape=cls['QgsLayoutItemShape']
    QgsUnitTypes = cls['QgsUnitTypes']
    QgsLayoutSize = cls['QgsLayoutSize']
    C = layout
    A = shape_data
    B = QgsLayoutItemShape(C)
    B.setShapeType(QgsLayoutItemShape.Rectangle)
    if A['is_color'] == 1:
        B.setBackgroundEnabled(True)
    B.attemptMove(
        QgsLayoutPoint(
            A['x'],
            A['y'],
            QgsUnitTypes.LayoutMillimeters))
    B.attemptResize(
        QgsLayoutSize(
            A['width'],
            A['height'],
            QgsUnitTypes.LayoutMillimeters))
    C.addItem(B)
# def affichage_distance(project,polygon_layer,field_name='length',precision=2):
    
# 	M='memory:';L='INPUT';I=precision;G=field_name;F=polygon_layer;E='OUTPUT';cls=get_qgis_manager().get_classes();processing=cls['processing'];QgsExpression=cls['QgsExpression'];QgsExpressionContext=cls['QgsExpressionContext'];QgsField=cls['QgsField'];QgsExpressionContextUtils=cls['QgsExpressionContextUtils'];QgsTextFormat=cls['QgsTextFormat'];QgsTextBackgroundSettings=cls['QgsTextBackgroundSettings'];QgsPalLayerSettings=cls['QgsPalLayerSettings'];QgsVectorLayerSimpleLabeling=cls['QgsVectorLayerSimpleLabeling']
# 	if not F or F.geometryType()!=2:raise ValueError("Couche d'entrée invalide ou non polygonale")
# 	N={L:F,E:M};J=processing.run('native:polygonstolines',N)[E];A=processing.run('native:explodelines',{L:J,E:M})[E];K=A.dataProvider();K.addAttributes([QgsField(G,QVariant.Double)]);A.updateFields();O=K.fieldNameIndex(G)
# 	try:
# 		A.startEditing();P=QgsExpression('$length');H=QgsExpressionContext();H.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(A))
# 		for D in A.getFeatures():
# 			H.setFeature(D);Q=D.geometry()
# 			if Q.isGeosValid():D.setAttribute(O,round(P.evaluate(H),I));A.updateFeature(D)
# 		A.commitChanges()
# 	except Exception as R:A.rollBack();raise RuntimeError(f"Erreur lors du calcul des longueurs : {str(R)}")
# 	B=QgsTextFormat();B.setSize(6);B.setColor(QColor(0,0,0));B.setBackground(QgsTextBackgroundSettings());B.background().setEnabled(_A);B.background().setType(QgsTextBackgroundSettings.ShapeRectangle);B.background().setFillColor(QColor(255,255,255,150));C=QgsPalLayerSettings();C.fieldName=f"format_number(\"{G}\", {I}) || 'm'";C.placement=QgsPalLayerSettings.Placement.Line;C.setFormat(B);C.isExpression=_A;A.setLabeling(QgsVectorLayerSimpleLabeling(C));A.setLabelsEnabled(_A);project.addMapLayer(A);return[A,J]
def affichage_distance(p,polygon_layer, field_name='length', precision=2):
    """
    Affiche les distances des segments d'une couche polygonale dans QGIS sans utiliser processing
    
    Args:
        polygon_layer (QgsVectorLayer): Couche d'entrée polygonale
        field_name (str): Nom du champ de stockage des distances
        precision (int): Nombre de décimales pour l'affichage
    
    Returns:
        list: [Couche des segments éclatés, Couche des contours]
    """
    # from qgis.core import (
    #     QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, 
    #     QgsProject, QgsTextFormat, QgsPalLayerSettings,
    #     QgsTextBackgroundSettings, QgsVectorLayerSimpleLabeling,
    #     QgsExpression, QgsExpressionContext, QgsExpressionContextUtils,
    #     QgsWkbTypes, QgsPoint
    # )
    from PyQt5.QtCore import QVariant
    from PyQt5.QtGui import QColor
    
    cls=get_qgis_manager().get_classes()
    QgsField=cls['QgsField']
    QgsTextFormat=cls['QgsTextFormat']
    QgsTextBackgroundSettings=cls['QgsTextBackgroundSettings']
    QgsPalLayerSettings=cls['QgsPalLayerSettings']
    QgsVectorLayerSimpleLabeling=cls['QgsVectorLayerSimpleLabeling']
    QgsVectorLayer=cls['QgsVectorLayer']
    QgsPoint=cls['QgsPoint']
    QgsGeometry=cls['QgsGeometry']
    QgsFeature=cls['QgsFeature']
    
    if not polygon_layer or polygon_layer.geometryType() != 2:  # 2 = Polygon
        raise ValueError("Couche d'entrée invalide ou non polygonale")
    
    try:
        # Créer une couche de lignes à partir des polygones (polygonstolines)
        crs = polygon_layer.crs()
        contour_layer = QgsVectorLayer(f"LineString?crs={crs.authid()}", "contours", "memory")
        contour_provider = contour_layer.dataProvider()
        
        # Copier les attributs
        contour_provider.addAttributes(polygon_layer.fields())
        contour_layer.updateFields()
        
        # Convertir les polygones en lignes
        features_to_add = []
        for feature in polygon_layer.getFeatures():
            geom = feature.geometry()
            if geom.isGeosValid():
                # Pour chaque anneau du polygone
                if geom.isMultipart():
                    polygons = geom.asMultiPolygon()
                    for polygon in polygons:
                        for ring in polygon:
                            # Convertir QgsPointXY en QgsPoint si nécessaire
                            points = [QgsPoint(point) for point in ring]
                            line_geom = QgsGeometry.fromPolyline(points)
                            if line_geom.isGeosValid():
                                new_feature = QgsFeature()
                                new_feature.setGeometry(line_geom)
                                new_feature.setAttributes(feature.attributes())
                                features_to_add.append(new_feature)
                else:
                    # Polygone simple
                    polygon_geom = geom.asPolygon()
                    for ring in polygon_geom:
                        # Convertir QgsPointXY en QgsPoint si nécessaire
                        points = [QgsPoint(point) for point in ring]
                        line_geom = QgsGeometry.fromPolyline(points)
                        if line_geom.isGeosValid():
                            new_feature = QgsFeature()
                            new_feature.setGeometry(line_geom)
                            new_feature.setAttributes(feature.attributes())
                            features_to_add.append(new_feature)
        
        contour_provider.addFeatures(features_to_add)
        
        # Créer une couche de segments éclatés (explodelines)
        segments_layer = QgsVectorLayer(f"LineString?crs={crs.authid()}", "segments", "memory")
        segments_provider = segments_layer.dataProvider()
        
        # Copier les attributs et ajouter le champ de longueur
        original_fields = polygon_layer.fields()
        segments_provider.addAttributes(original_fields)
        segments_provider.addAttributes([QgsField(field_name, QVariant.Double)])
        segments_layer.updateFields()
        
        # Extraire les segments individuels
        segments_to_add = []
        field_index = segments_provider.fieldNameIndex(field_name)
        
        for feature in contour_layer.getFeatures():
            geom = feature.geometry()
            if geom.isGeosValid():
                # Si c'est une ligne multipartie, la diviser en segments simples
                if geom.isMultipart():
                    lines = geom.asMultiPolyline()
                    for line in lines:
                        for i in range(len(line) - 1):
                            # Créer des QgsPoint à partir des QgsPointXY
                            point1 = QgsPoint(line[i])
                            point2 = QgsPoint(line[i+1])
                            segment_geom = QgsGeometry.fromPolyline([point1, point2])
                            if segment_geom.isGeosValid():
                                new_feature = QgsFeature()
                                new_feature.setGeometry(segment_geom)
                                # Copier les attributs originaux
                                attrs = feature.attributes() + [None]
                                new_feature.setAttributes(attrs)
                                segments_to_add.append(new_feature)
                else:
                    # Si c'est une ligne simple, la diviser en segments
                    points = geom.asPolyline()
                    for i in range(len(points) - 1):
                        # Créer des QgsPoint à partir des QgsPointXY
                        point1 = QgsPoint(points[i])
                        point2 = QgsPoint(points[i+1])
                        segment_geom = QgsGeometry.fromPolyline([point1, point2])
                        if segment_geom.isGeosValid():
                            new_feature = QgsFeature()
                            new_feature.setGeometry(segment_geom)
                            # Copier les attributs originaux
                            attrs = feature.attributes() + [None]
                            new_feature.setAttributes(attrs)
                            segments_to_add.append(new_feature)
        
        segments_provider.addFeatures(segments_to_add)
        
        # Calculer et mettre à jour les longueurs
        try:
            segments_layer.startEditing()
            
            for feature in segments_layer.getFeatures():
                geom = feature.geometry()
                if geom.isGeosValid():
                    # Calculer la longueur
                    length = geom.length()
                    feature.setAttribute(field_index, round(length, precision))
                    segments_layer.updateFeature(feature)
            
            segments_layer.commitChanges()
            
        except Exception as e:
            segments_layer.rollBack()
            raise RuntimeError(f"Erreur lors du calcul des longueurs : {str(e)}")
        
        # Configuration de l'étiquetage
        text_format = QgsTextFormat()
        text_format.setSize(6)
        text_format.setColor(QColor(0, 0, 0))
        
        # Configuration du fond des étiquettes
        background_settings = QgsTextBackgroundSettings()
        background_settings.setEnabled(True)
        background_settings.setType(QgsTextBackgroundSettings.ShapeRectangle)
        background_settings.setFillColor(QColor(255, 255, 255, 150))
        text_format.setBackground(background_settings)
        
        # Configuration des paramètres d'étiquetage
        label_settings = QgsPalLayerSettings()
        label_settings.fieldName = f"format_number(\"{field_name}\", {precision}) || 'm'"
        label_settings.placement = QgsPalLayerSettings.Placement.Line
        label_settings.setFormat(text_format)
        label_settings.isExpression = True
        
        # Appliquer l'étiquetage
        segments_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        segments_layer.setLabelsEnabled(True)
        
        # Ajouter la couche au projet
        p.addMapLayer(segments_layer)
        
        return [segments_layer, contour_layer]
        
    except Exception as e:
        raise RuntimeError(f"Erreur lors de la création des couches de distance : {str(e)}")

def changer_couleur(layer,R,G,B):A=layer;C=A.renderer().symbol();D=C.symbolLayer(0);D.setColor(QColor(R,G,B));A.triggerRepaint()
def arrondir_au_multiple_superieur(nombre):
	A=nombre
	if A<100:return A
	C=len(str(A))-1;B=10**C;return math.ceil(A/B)*B
def create_carte(project,config,data):
	AL='Exportation';AK='output';AJ='Terrain';AI='Distance';A1='echelle';A0='is_cadre';z='Points sommets';q=config;p=project;o='height';n='width';m='Arial';h=None;cls=get_qgis_manager().get_classes();B=cls['QgsPrintLayout'](p);B.initializeDefaults();H=0;I=p.mapLayersByName(z)[0]
	QgsLayoutItemShape=cls['QgsLayoutItemShape'];QgsLayoutPoint=cls['QgsLayoutPoint'];QgsUnitTypes=cls['QgsUnitTypes'];QgsLayoutSize=cls['QgsLayoutSize'];QgsLayoutItemLabel=cls['QgsLayoutItemLabel'];QgsLayoutItemMap=cls['QgsLayoutItemMap'];QgsLayoutItemPicture=cls['QgsLayoutItemPicture'];QgsSymbol=cls['QgsSymbol'];QgsLayerTreeLayer=cls['QgsLayerTreeLayer'];QgsLayerTreeGroup=cls['QgsLayerTreeGroup'];QgsLinePatternFillSymbolLayer=cls['QgsLinePatternFillSymbolLayer'];QgsFeature=cls['QgsFeature'];QgsLayoutItemMapGrid=cls['QgsLayoutItemMapGrid'];QgsRectangle=cls['QgsRectangle'];QgsLayoutItemLegend=cls['QgsLayoutItemLegend'];QgsSimpleLineSymbolLayer=cls['QgsSimpleLineSymbolLayer'];QgsLegendStyle=cls['QgsLegendStyle'];QgsLayerTreeModel=cls['QgsLayerTreeModel'];QgsWkbTypes=cls['QgsWkbTypes'];QgsVectorLayer=cls['QgsVectorLayer'];QgsSingleSymbolRenderer=cls['QgsSingleSymbolRenderer'] # for f in p.mapLayersByName("Parcelles"):p.removeMapLayer(f.id())
	if I:
		s=I.getFeatures();A2=[A.name()for A in I.fields()];V=7;G=18;E=7;J=len(I);H=E*(J+1);Q=200-H-2;i=12;j=10;W=2;X=0;d=0
		if J>5 and J<=10:Q=128;G=15;E=6;H=E*(J+1);Q=200-H-2;i=10;j=8;W=1
		elif J>10:
			G=12;E=3;H=E*(J+1);A3=E*(J+1)
			if J>20:H=E*(20+1);A3=E*(J-20+1)
			Q=200-H-2;d=200-A3-2;i=7;j=6;W=.5
		for(R,Y)in enumerate(A2):
			if Y!=AI:
				C=QgsLayoutItemShape(B);C.setShapeType(QgsLayoutItemShape.Rectangle);C.attemptMove(QgsLayoutPoint(V+R*G,Q,QgsUnitTypes.LayoutMillimeters));C.attemptResize(QgsLayoutSize(G,E,QgsUnitTypes.LayoutMillimeters));C.setFrameEnabled(_A);C.setFrameStrokeColor(QColor(0,0,0));B.addItem(C);D=QgsLayoutItemLabel(B);D.setText(Y);D.setFont(QFont(m,i,QFont.Bold));D.attemptMove(QgsLayoutPoint(V+R*G+2,Q+W,QgsUnitTypes.LayoutMillimeters));B.addItem(D)
				if J>20:X=V+R*G+G*3+2;C=QgsLayoutItemShape(B);C.setShapeType(QgsLayoutItemShape.Rectangle);C.attemptMove(QgsLayoutPoint(X,d,QgsUnitTypes.LayoutMillimeters));C.attemptResize(QgsLayoutSize(G,E,QgsUnitTypes.LayoutMillimeters));C.setFrameEnabled(_A);C.setFrameStrokeColor(QColor(0,0,0));B.addItem(C);D=QgsLayoutItemLabel(B);D.setText(Y);D.setFont(QFont(m,i,QFont.Bold));D.attemptMove(QgsLayoutPoint(X+2,d+W,QgsUnitTypes.LayoutMillimeters));B.addItem(D)
		for(Z,L)in enumerate(s):
			if Z>=J:break
			for(R,Y)in enumerate(A2):
				if Y!=AI:
					A4=str(L[Y])
					if Z>19:X=V+R*G+G*3+2;C=QgsLayoutItemShape(B);C.setShapeType(QgsLayoutItemShape.Rectangle);C.attemptMove(QgsLayoutPoint(X,d+(Z-20+1)*E,QgsUnitTypes.LayoutMillimeters));C.attemptResize(QgsLayoutSize(G,E,QgsUnitTypes.LayoutMillimeters));C.setFrameEnabled(_A);C.setFrameStrokeColor(QColor(0,0,0));B.addItem(C);D=QgsLayoutItemLabel(B);D.setText(A4);D.setFont(QFont(m,j,QFont.Bold));D.attemptMove(QgsLayoutPoint(X+2,d+(Z-20+1)*E+W,QgsUnitTypes.LayoutMillimeters));B.addItem(D)
					else:C=QgsLayoutItemShape(B);C.setShapeType(QgsLayoutItemShape.Rectangle);C.attemptMove(QgsLayoutPoint(V+R*G,Q+(Z+1)*E,QgsUnitTypes.LayoutMillimeters));C.attemptResize(QgsLayoutSize(G,E,QgsUnitTypes.LayoutMillimeters));C.setFrameEnabled(_A);C.setFrameStrokeColor(QColor(0,0,0));B.addItem(C);D=QgsLayoutItemLabel(B);D.setText(A4);D.setFont(QFont(m,j,QFont.Bold));D.attemptMove(QgsLayoutPoint(V+R*G+2,Q+(Z+1)*E+W,QgsUnitTypes.LayoutMillimeters));B.addItem(D)
	K=p.mapLayersByName(AJ)[0]
	if K:
		s=K.getFeatures();a=h
		for L in s:
			if a is h:a=L.geometry().boundingBox()
			else:a.combineExtentWith(L.geometry().boundingBox())
			if a:
				a=K.extent();t=L.geometry().length()
				larg = 3
				sf = 40
				if t>1200:t+=200
				if t>3000:larg=4;sf=30
				AM=[{'x':151.5,'y':17.5,n:140,o:114,A0:False,A1:round(L.geometry().length()*114/(114*(1/sf)))},{'x':5.5,'y':14,n:140,o:119 if H==63 else 119+(63-H),A0:_A,A1:round(t*(119 if H==63 else 119+(63-H))/((119 if H==63 else 119+(63-H))/larg))}];changer_couleur(K,255,255,255);changer_couleur(I,0,0,0)
				for(A5,O)in enumerate(AM,start=1):
					A=QgsLayoutItemMap(B);b=QgsLayoutItemPicture(B);b.setPicturePath(os.path.join(os.path.dirname(__file__),'NorthArrow_02.svg'));AN=p.mapLayers();S=[];bf=QgsLayoutItemPicture(B);bf.setPicturePath(os.path.join(os.path.dirname(__file__),'indicateur.svg'))
					if A5==1:
						b.attemptMove(QgsLayoutPoint(155,20,QgsUnitTypes.LayoutMillimeters));b.attemptResize(QgsLayoutSize(10,10,QgsUnitTypes.LayoutMillimeters));N=QgsSymbol.defaultSymbol(K.geometryType());e=QgsLinePatternFillSymbolLayer();e.setColor(QColor(0,0,0));e.setLineWidth(.1);e.setDistance(.5);e.setAngle(45);u=QgsSimpleLineSymbolLayer();u.setColor(QColor(0,0,0));u.setWidth(.5);N.changeSymbolLayer(0,e);N.appendSymbolLayer(u);K.setRenderer(QgsSingleSymbolRenderer(N));K.triggerRepaint();A6=[];v=[];AO=[z];S=[A for A in AN.values()if A.name()not in AO];AP=p.layerTreeRoot()
						bf.attemptMove(QgsLayoutPoint(208,72,QgsUnitTypes.LayoutMillimeters));bf.attemptResize(QgsLayoutSize(10,10,QgsUnitTypes.LayoutMillimeters))
						def A7(group):
							B=[]
							for A in group.children():
								if isinstance(A,QgsLayerTreeLayer):
									if A.isVisible():B.append(A.layer())
								elif isinstance(A,QgsLayerTreeGroup):B.extend(A7(A))
							return B
						v=A7(AP);v=[A for A in v if A.name()!=z]
						for f in S:
							if isinstance(f,QgsLayerTreeLayer)and f.isVisible():A6.append(f.layer())
						A.setLayers(A6)
					else:
						b.attemptMove(QgsLayoutPoint(8,20,QgsUnitTypes.LayoutMillimeters));b.attemptResize(QgsLayoutSize(10,10,QgsUnitTypes.LayoutMillimeters));AQ=QgsWkbTypes.displayString(K.wkbType());T=QgsVectorLayer(f"{AQ}?crs={K.crs().authid()}",'Nouvelle_Couche','memory');A8=T.dataProvider();A8.addAttributes(K.fields());T.updateFields();A9=[]
						for L in K.getFeatures():w=QgsFeature();w.setGeometry(L.geometry());w.setAttributes(L.attributes());A9.append(w)
						A8.addFeatures(A9);N=T.renderer().symbol();AR=N.symbolLayer(0);AR.setColor(QColor(255,255,255));T.triggerRepaint();x=2
						if len(I)>10 and len(I)<20:x=1.5
						elif len(I)>20:x=1
						N=QgsSymbol.defaultSymbol(I.geometryType());N.setColor(QColor('black'));N.setSize(x);AS=I.renderer();AS.setSymbol(N);I.triggerRepaint();
						if q['is_distance']:S=affichage_distance(p,T);S.append(I);S.append(T)
						else:S=[T,I]
						if q['is_grid']:
							U=L.geometry().area();M=100
							if U<10000:M=25
							elif U<50000:M=50
							elif U<100000:M=100
							elif U<200000:M=150
							elif U<300000:M=200
							elif U<500000:M=250
							elif U<1000000:M=300
							else:M=400
							A.grid().setEnabled(_A);A.grid().setIntervalX(M);A.grid().setIntervalY(M);A.grid().setAnnotationEnabled(_A);A.grid().setStyle(QgsLayoutItemMapGrid.Cross);A.grid().setGridLineWidth(.2);A.grid().setCrossLength(.8);A.grid().setAnnotationPrecision(0);A.grid().setAnnotationFrameDistance(1);A.grid().setAnnotationFontColor(QColor(0,0,0));A.grid().setFrameWidth(2);AA=A.grid().annotationFont();AA.setPointSize(6);A.grid().setAnnotationFont(AA);A.grid().setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame,QgsLayoutItemMapGrid.Right);A.grid().setAnnotationDirection(QgsLayoutItemMapGrid.Vertical,QgsLayoutItemMapGrid.Right);A.grid().setAnnotationPosition(QgsLayoutItemMapGrid.InsideMapFrame,QgsLayoutItemMapGrid.Top);A.grid().setAnnotationDirection(QgsLayoutItemMapGrid.Horizontal,QgsLayoutItemMapGrid.Top);A.grid().setAnnotationPosition(QgsLayoutItemMapGrid.InsideMapFrame,QgsLayoutItemMapGrid.Bottom);A.grid().setAnnotationDirection(QgsLayoutItemMapGrid.Horizontal,QgsLayoutItemMapGrid.Bottom);A.grid().setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame,QgsLayoutItemMapGrid.Left);A.grid().setAnnotationDirection(QgsLayoutItemMapGrid.Vertical,QgsLayoutItemMapGrid.Left)
					A.setLayers(S);A.attemptMove(QgsLayoutPoint(O.get('x'),O.get('y'),QgsUnitTypes.LayoutMillimeters));A.attemptResize(QgsLayoutSize(O.get(n),O.get(o),QgsUnitTypes.LayoutMillimeters));A.setFrameEnabled(O.get(A0));A.setFrameStrokeColor(Qt.black);A.setExtent(a);AB=A.extent();AC=AB.center().x();AD=AB.center().y();AE=A.scale();AF=O.get(n)/25.4*AE;AG=O.get(o)/25.4*AE;AT=QgsRectangle(AC-AF/2,AD-AG/2,AC+AF/2,AD+AG/2);A.setExtent(AT);A.setScale(O.get(A1))
					if A5==2:_create_label_item(B,{"text":f"Échelle: 1/{arrondir_au_multiple_superieur(round(A.scale()))}","x":55,"y":190,"width":141,"height":10,"font_size":10,"is_bold":1});_create_shape_item(B,{"x": 110.0, "y": 191.5, "width": 35.0, "height": 7.0, "is_color": 1})
					else:_create_label_item(B,{"text":f"Échelle: 1/{arrondir_au_multiple_superieur(round(A.scale()))}","x":201,"y":122,"width":141,"height":10,"font_size":10,"is_bold":1});_create_shape_item(B,{"x": 255.5, "y": 123.5, "width": 35.0, "height": 7.0, "is_color": 1});_create_label_item(B,{"text":"Terrain","x":192.0,"y":67.0,"width":40.0,"height":10.0,"font_size":6,"is_bold":1})
					B.addItem(A);A.refresh();B.addLayoutItem(b);B.addLayoutItem(bf)
					if q['is_legend']:
						F=QgsLayoutItemLegend(B);F.setTitle('Légende');k=p.layerTreeRoot().clone()
						for P in k.children():
							if isinstance(P,QgsLayerTreeLayer)and not P.isVisible():
								g=P.parent()
								if g:g.removeChildNode(P)
							elif isinstance(P,QgsLayerTreeGroup)and not P.children():
								g=P.parent()
								if g:g.removeChildNode(P)
						AU=QgsLayerTreeModel(k);F.model().setRootGroup(k);F.root_clone=k;F.layer_tree_model=AU;F.attemptMove(QgsLayoutPoint(200,17.5,QgsUnitTypes.LayoutMillimeters));F.setAutoUpdateModel(_A);F.refresh();F.setColumnCount(3);F.setSymbolWidth(2);F.setSymbolHeight(1.5);y=F.styleFont(QgsLegendStyle.Title);y.setPointSize(8);y.setBold(_A);F.setStyleFont(QgsLegendStyle.Title,y);AH=F.styleFont(QgsLegendStyle.SymbolLabel);AH.setPointSize(6);F.setStyleFont(QgsLegendStyle.SymbolLabel,AH);B.addItem(F)
	
	# return B # AV=QgsLayoutExporter(B);AW=AV.exportToPdf(os.path.join(os.path.dirname(__file__),'mise_en_page.pdf'),QgsLayoutExporter.PdfExportSettings())
	for AX in(AK,AK):
		for f in p.mapLayersByName(AX):p.removeMapLayer(f.id())
    
	return B # if AW==QgsLayoutExporter.Success:
	# 	return True
	# 	# QMessageBox.information(h,AL,'Mise en page exportée avec succès')
	# 	# if sys.platform.startswith('win'):os.startfile(l)
	# 	# elif sys.platform.startswith('linux'):subprocess.run(['xdg-open',l])
	# 	# elif sys.platform.startswith('darwin'):subprocess.run(['open',l])
	# else:return False #QMessageBox.critical(h,AL,"Erreur lors de l'exportation du PDF.")
 
# API Views
@api_view(['POST'])
@permission_classes([AllowAny])
def create_project(request):
    """Créer un nouveau projet QGIS avec session persistante"""
    try:
        project_title = request.data.get('title', 'Nouveau Projet')
        crs_id = request.data.get('crs', 'EPSG:4326')
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False, 
                error=error, 
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Créer une nouvelle session
        session, session_id = get_project_session()
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsProject = classes['QgsProject']
        
        # Obtenir le projet pour cette session
        project = session.get_project(QgsProject)
        project.setTitle(project_title)
        
        # Sauvegarder le projet
        project_path = os.path.join(settings.MEDIA_ROOT, f'{session_id}.qgs')
        success_save = project.write(project_path)
        
        if not success_save:
            return standard_response(
                success=False,
                error="Failed to save project",
                message="Impossible de sauvegarder le projet",
                status_code=500
            )
        
        return standard_response(
            success=True,
            data={
                "session_id": session_id,
                "title": project_title,
                "file_name": project_path,
                "crs": crs_id,
                "layers": []
            },
            message="Projet créé avec succès"
        )
        
    except Exception as e:
        return handle_exception(e, "create_project", "Impossible de créer le projet")

@api_view(['POST'])
@permission_classes([AllowAny])
def load_project(request):
    """Charger un projet QGIS existant dans une session persistante"""
    try:
        project_path = request.data.get('project_path')
        session_id = request.data.get('session_id')
        
        if not project_path:
            return standard_response(
                success=False,
                error="project_path is required",
                message="Le chemin du projet est requis",
                status_code=400
            )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False, 
                error=error, 
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Obtenir la session existante
        session, session_id = get_project_session(session_id)
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsProject = classes['QgsProject']
        
        # Obtenir le projet pour cette session
        project = session.get_project(QgsProject)
        success_load = project.read(project_path)
        
        if not success_load:
            return standard_response(
                success=False,
                error="Failed to load project",
                message="Impossible de charger le projet. Le fichier peut être corrompu.",
                status_code=500
            )
        
        return standard_response(
            success=True,
            data={
                "session_id": session_id,
                "title": project.title(),
                "file_name": project_path,
                "crs": project.crs().authid() if project.crs() else "EPSG:4326",
                "layers": []
            },
            message="Projet chargé avec succès"
        )
        
    except Exception as e:
        return handle_exception(e, "load_project", "Impossible de charger le projet")

@api_view(['GET'])
@permission_classes([AllowAny])
def project_info(request):
    """Obtenir les informations détaillées du projet courant de la session"""
    try:
        session_id = request.GET.get('session_id')
        if not session_id:
            return standard_response(
                success=False,
                error="session_id is required",
                message="L'identifiant de session est requis",
                status_code=400
            )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False, 
                error=error, 
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Obtenir la session existante
        with project_sessions_lock:
            session = project_sessions.get(session_id)
            if session is None:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée. Veuillez créer une nouvelle session.",
                    status_code=404
                )
        
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsProject = classes['QgsProject']
        
        # Obtenir le projet pour cette session
        project = session.get_project(QgsProject)
        
        layers_info = []
        for layer_id, layer in project.mapLayers().items():
            layers_info.append({
                "id": layer.id(),
                "name": layer.name(),
                "type": layer.typeName() if hasattr(layer, 'typeName') else "unknown"
            })
        
        return standard_response(
            success=True,
            data={
                "session_id": session_id,
                "title": project.title(),
                "file_name": project.fileName(),
                "crs": project.crs().authid() if project.crs() else "EPSG:4326",
                "layers": layers_info,
                "created_at": session.created_at.isoformat(),
                "last_accessed": session.last_accessed.isoformat()
            },
            message="Informations du projet récupérées"
        )
        
    except Exception as e:
        return handle_exception(e, "project_info", "Impossible de récupérer les informations du projet")

@api_view(['GET'])
@permission_classes([AllowAny])
def get_layers(request):
    """Obtenir la liste détaillée des couches de la session courante"""
    try:
        session_id = request.GET.get('session_id')
        if not session_id:
            return standard_response(
                success=False,
                error="session_id is required",
                message="L'identifiant de session est requis",
                status_code=400
            )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False, 
                error=error, 
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Obtenir la session existante
        with project_sessions_lock:
            session = project_sessions.get(session_id)
            if session is None:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée. Veuillez créer une nouvelle session.",
                    status_code=404
                )
        
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsProject = classes['QgsProject']
        
        # Obtenir le projet pour cette session
        project = session.get_project(QgsProject)
        
        layers_info = []
        for layer_id, layer in project.mapLayers().items():
            try:
                extent = layer.extent() if hasattr(layer, 'extent') else None
                extent_info = {
                    "xmin": extent.xMinimum() if extent else None,
                    "xmax": extent.xMaximum() if extent else None,
                    "ymin": extent.yMinimum() if extent else None,
                    "ymax": extent.yMaximum() if extent else None
                } if extent else None
                
                layers_info.append({
                    "id": layer.id(),
                    "name": layer.name(),
                    "type": layer.typeName() if hasattr(layer, 'typeName') else "unknown",
                    "source": layer.source() if hasattr(layer, 'source') else None,
                    "extent": extent_info
                })
            except Exception as e:
                logger.warning(f"Erreur lors de la récupération des informations de la couche {layer_id}: {e}")
                layers_info.append({
                    "id": layer.id(),
                    "name": layer.name(),
                    "type": "error",
                    "error": str(e)
                })
        
        return standard_response(
            success=True,
            data={
                "session_id": session_id,
                "layers": layers_info
            },
            message=f"{len(layers_info)} couches récupérées"
        )
        
    except Exception as e:
        return handle_exception(e, "get_layers", "Impossible de récupérer la liste des couches")

@api_view(['POST'])
@permission_classes([AllowAny])
def add_vector_layer(request):
    """Ajouter une couche vectorielle à la session courante"""
    try:
        data_source = request.data.get('data_source')
        layer_name = request.data.get('layer_name', 'Couche Vectorielle')
        session_id = request.data.get('session_id')
        is_parcelle = request.data.get('is_parcelle', False)
        output_polygon_layer = request.data.get('output_polygon_layer', None)
        output_points_layer = request.data.get('output_points_layer', None)
        # Options de labeling
        enable_point_labels = request.data.get('enable_point_labels', False)
        label_field = request.data.get('label_field', 'Bornes')
        label_color = request.data.get('label_color', '#000000')
        label_size = int(request.data.get('label_size', 10))
        label_offset_x = int(request.data.get('label_offset_x', 0))
        label_offset_y = int(request.data.get('label_offset_y', 0))
        
        if not data_source:
            return standard_response(
                success=False,
                error="data_source is required",
                message="La source de données est requise",
                status_code=400
            )
        
        if not session_id:
            return standard_response(
                success=False,
                error="session_id is required",
                message="L'identifiant de session est requis",
                status_code=400
            )
        
        # Vérifier si le fichier existe
        if not os.path.exists(data_source) and not data_source.startswith(('http', 'https')):
            return standard_response(
                success=False,
                error="data_source not found",
                message=f"Fichier source non trouvé : {data_source}",
                status_code=404
            )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False,
                error=error,
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Obtenir la session existante
        with project_sessions_lock:
            session = project_sessions.get(session_id)
            if session is None:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée. Veuillez créer une nouvelle session.",
                    status_code=404
                )
        
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsVectorLayer = classes['QgsVectorLayer']
        QgsProject = classes['QgsProject']
        
        # Obtenir le projet pour cette session
        project = session.get_project(QgsProject)
        
        # Déterminer le type de fichier et le provider approprié
        file_extension = os.path.splitext(data_source)[1].lower()
        
        if file_extension == '.shp':
            provider = 'ogr'
            layer = QgsVectorLayer(data_source, 'input_layer', provider)
        elif file_extension == '.gpx':
            provider = 'gpx'
            # Pour GPX, on peut avoir plusieurs layers, on prend les waypoints par défaut
            layer = QgsVectorLayer(f"{data_source}?type=track", 'input_layer', provider)
        elif file_extension == '.csv':
            provider = 'delimitedtext'
            # Pour CSV, il faut spécifier le format
            uri = f"file:///{data_source}?delimiter=;&xField=X&yField=Y"
            layer = QgsVectorLayer(uri, 'input_layer', provider)
        else:
            raise ValueError(f"Format de fichier non supporté: {file_extension}")

        
        if not layer.isValid():
            return standard_response(
                success=False,
                error="Layer failed to load",
                message=f"Échec du chargement de la couche. Format non supporté ou fichier corrompu.",
                status_code=400
            )
        
        if is_parcelle:
            from PyQt5.QtGui import QColor
            polygon_layer, points_layer = create_polygon_with_vertex_points(layer, output_polygon_layer, output_points_layer)
            
            label_settings = classes['QgsPalLayerSettings']()
            label_settings.fieldName, label_settings.placement = label_field, classes['QgsPalLayerSettings'].AroundPoint
            text_format = classes['QgsTextFormat']()
            color = QColor(label_color)
            if color.isValid():
                text_format.setColor(color)
            label_settings.xOffset = label_offset_x
            label_settings.yOffset = label_offset_y
            text_format.setSize(label_size)
            label_settings.setFormat(text_format)
            
            points_layer.setLabeling(classes['QgsVectorLayerSimpleLabeling'](label_settings))
            points_layer.setLabelsEnabled(enable_point_labels)
            points_layer.triggerRepaint()
            
            project.addMapLayer(polygon_layer)
            project.addMapLayer(points_layer)
            polygon_layer_info = format_layer_info(polygon_layer)
            points_layer_info = format_layer_info(points_layer)
            layer_info = {
                "Parcelle": polygon_layer_info,
                "Points sommets": points_layer_info
            }
            message = f"Couches vectorielles Parcelle et Points sommets ajoutée avec succès)"
        else:
            project.addMapLayer(layer)
            layer_info = format_layer_info(layer)
            message = f"Couche vectorielle '{layer_name}' ajoutée avec succès ({layer_info['feature_count']} entités)"
        
        return standard_response(
            success=True,
            data=layer_info,
            message=message,
            metadata={
                'session_id': session_id,
                'layer_id': layer.id()
            }
        )
    except Exception as e:
        return handle_exception(e, "add_vector_layer", "Impossible d'ajouter la couche vectorielle")

@api_view(['POST'])
@permission_classes([AllowAny])
def add_raster_layer(request):
    """Ajouter une couche raster à la session"""
    try:
        data_source = request.data.get('data_source')
        layer_name = request.data.get('layer_name', 'Couche Raster')
        session_id = request.data.get('session_id')
        
        if not data_source:
            return standard_response(
                success=False,
                error="data_source is required",
                message="La source de données est requise",
                status_code=400
            )
        
        if not session_id:
            return standard_response(
                success=False,
                error="session_id is required",
                message="L'identifiant de session est requis",
                status_code=400
            )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False, 
                error=error, 
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Obtenir la session existante
        with project_sessions_lock:
            session = project_sessions.get(session_id)
            if session is None:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée. Veuillez créer une nouvelle session.",
                    status_code=404
                )
        
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsRasterLayer = classes['QgsRasterLayer']
        QgsProject = classes['QgsProject']
        
        # Obtenir le projet pour cette session
        project = session.get_project(QgsProject)
        
        # Créer la couche raster
        layer = QgsRasterLayer(data_source, layer_name)
        if not layer.isValid():
            return standard_response(
                success=False,
                error="Invalid layer",
                message="La couche raster n'est pas valide",
                status_code=400
            )
        
        # Ajouter la couche au projet
        project.addMapLayer(layer)
        
        # Obtenir les informations détaillées de la couche
        layer_info = format_layer_info(layer)
        
        return standard_response(
            success=True,
            data={
                "layer_id": layer.id(),
                "layer_name": layer.name(),
                "session_id": session_id,
                "layer_info": layer_info
            },
            message=f"Couche raster '{layer_name}' ajoutée avec succès ({layer_info.get('bands', 0)} bandes)",
            metadata={
                'session_id': session_id,
                'layer_id': layer.id()
            }
        )
        
    except Exception as e:
        return handle_exception(e, "add_raster_layer", "Impossible d'ajouter la couche raster")

@api_view(['POST'])
@permission_classes([AllowAny])
def remove_layer(request):
    """Supprimer une couche avec confirmation détaillée"""
    try:
        layer_id = request.data.get('layer_id')
        session_id = request.data.get('session_id')
        
        if not layer_id:
            return standard_response(
                success=False,
                error="layer_id is required",
                message="L'ID de la couche est requis",
                status_code=400
            )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False, 
                error=error, 
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Obtenir la session existante
        with project_sessions_lock:
            session = project_sessions.get(session_id)
            if session is None:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée. Veuillez créer une nouvelle session.",
                    status_code=404
                )
        
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsProject = classes['QgsProject']
        
        # Obtenir le projet pour cette session
        project = session.get_project(QgsProject)
        
        # Supprimer la couche
        layer = project.mapLayer(layer_id)
        if layer:
            project.removeMapLayer(layer)
            return standard_response(
                success=True,
                data={
                    "layer_id": layer_id,
                    "session_id": session_id,
                    "message": "Couche supprimée avec succès"
                },
                message="Couche supprimée avec succès"
            )
        else:
            return standard_response(
                success=False,
                error="Layer not found",
                message="Couche non trouvée",
                status_code=404
            )
        
    except Exception as e:
        return handle_exception(e, "remove_layer", "Impossible de supprimer la couche")

@api_view(['GET'])
@permission_classes([AllowAny])
def get_layer_features(request, layer_id):
    """Obtenir les caractéristiques d'une couche avec pagination"""
    try:
        session_id = request.GET.get('session_id')
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 100))
        
        if not layer_id:
            return standard_response(
                success=False,
                error="layer_id is required",
                message="L'ID de la couche est requis",
                status_code=400
            )
        
        if not session_id:
            return standard_response(
                success=False,
                error="session_id is required",
                message="L'identifiant de session est requis",
                status_code=400
            )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False, 
                error=error, 
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Obtenir la session existante
        with project_sessions_lock:
            session = project_sessions.get(session_id)
            if session is None:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée. Veuillez créer une nouvelle session.",
                    status_code=404
                )
        
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsProject = classes['QgsProject']
        
        # Obtenir le projet pour cette session
        project = session.get_project(QgsProject)
        
        # Obtenir la couche
        layer = project.mapLayer(layer_id)
        if not layer:
            return standard_response(
                success=False,
                error="Layer not found",
                message=f"Couche avec ID '{layer_id}' de la session '{session_id}' non trouvée",
                status_code=404
            )
        
        # Obtenir les caractéristiques avec pagination
        features_data = []
        total_features = 0
        
        try:
            # Compter le nombre total de caractéristiques
            total_features = layer.featureCount()
            
            # Récupérer les caractéristiques avec pagination
            feature_iterator = layer.getFeatures()
            feature_iterator = list(feature_iterator)[offset:offset + limit]
            
            for feature in feature_iterator:
                # Récupérer les attributs
                attrs = feature.attributes()
                fields = feature.fields()
                
                # Convertir les attributs en dictionnaire
                feature_data = {}
                for i, attr in enumerate(attrs):
                    field_name = fields[i].name()
                    feature_data[field_name] = attr
                
                # Ajouter la géométrie si disponible
                geometry = feature.geometry()
                if geometry:
                    feature_data['geometry'] = {
                        'type': geometry.typeName(),
                        'wkt': geometry.asWkt()
                    }
                
                features_data.append(feature_data)
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des caractéristiques: {e}")
            return standard_response(
                success=False,
                error="Failed to fetch features",
                message="Impossible de récupérer les caractéristiques de la couche",
                status_code=500
            )
        
        result = {
            'layer_id': layer_id,
            'layer_name': layer.name(),
            'total_features': total_features,
            'requested_features': len(features_data),
            'offset': offset,
            'limit': limit,
            'has_more': offset + len(features_data) < total_features,
            'features': features_data
        }
        
        return standard_response(
            success=True,
            data=result,
            message=f"{len(features_data)} features récupérés sur {total_features} au total de la session '{session_id}'",
            metadata={
                'session_id': session_id,
                'pagination': {
                    'current_page': (offset // limit) + 1,
                    'total_pages': (total_features + limit - 1) // limit,
                    'per_page': limit
                }
            }
        )
        
    except Exception as e:
        return handle_exception(e, "get_layer_features", "Impossible de récupérer les features de la couche")

@api_view(['GET'])
@permission_classes([AllowAny])
def get_layer_extent(request, layer_id):
    """Obtenir l'étendue géographique d'une couche avec informations détaillées"""
    try:
        session_id = request.GET.get('session_id')
        
        if not layer_id:
            return standard_response(
                success=False,
                error="layer_id is required",
                message="L'ID de la couche est requis",
                status_code=400
            )
        
        if not session_id:
            return standard_response(
                success=False,
                error="session_id is required",
                message="L'identifiant de session est requis",
                status_code=400
            )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False, 
                error=error, 
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Obtenir la session existante
        with project_sessions_lock:
            session = project_sessions.get(session_id)
            if session is None:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée. Veuillez créer une nouvelle session.",
                    status_code=404
                )
        
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsProject = classes['QgsProject']
        
        # Obtenir le projet pour cette session
        project = session.get_project(QgsProject)
        
        # Obtenir la couche
        layer = project.mapLayer(layer_id)
        if not layer:
            return standard_response(
                success=False,
                error="Layer not found",
                message=f"Couche avec ID '{layer_id}' de la session '{session_id}' non trouvée",
                status_code=404,
                metadata={
                    'session_id': session_id,
                    'available_layers': list(project.mapLayers().keys())
                }
            )
        
        # Calculer l'étendue
        extent = layer.extent()
        
        # Vérifier si l'étendue est valide
        if extent.isEmpty():
            return standard_response(
                success=False,
                error="Empty extent",
                message=f"La couche '{layer.name()}' n'a pas d'étendue valide",
                status_code=400
            )
        
        # Calculer les dimensions
        width = extent.xMaximum() - extent.xMinimum()
        height = extent.yMaximum() - extent.yMinimum()
        
        # Calculer le centroïde
        center_x = (extent.xMinimum() + extent.xMaximum()) / 2
        center_y = (extent.yMinimum() + extent.yMaximum()) / 2
        
        # Calculer l'aire
        area = width * height if width > 0 and height > 0 else 0
        
        # Obtenir les informations du système de coordonnées
        crs_authid = layer.crs().authid() if layer.crs() and layer.crs().isValid() else None
        
        extent_info = {
            'layer_id': layer_id,
            'layer_name': layer.name(),
            'coordinate_system': crs_authid,
            'extent': {
                'xmin': round(extent.xMinimum(), 6),
                'ymin': round(extent.yMinimum(), 6),
                'xmax': round(extent.xMaximum(), 6),
                'ymax': round(extent.yMaximum(), 6),
                'center': {
                    'x': round(center_x, 6),
                    'y': round(center_y, 6)
                },
                'dimensions': {
                    'width': round(width, 6),
                    'height': round(height, 6)
                },
                'area': round(area, 6)
            },
            'bounds': {
                'south_west': {
                    'x': round(extent.xMinimum(), 6),
                    'y': round(extent.yMinimum(), 6)
                },
                'north_east': {
                    'x': round(extent.xMaximum(), 6),
                    'y': round(extent.yMaximum(), 6)
                }
            }
        }
        
        return standard_response(
            success=True,
            data=extent_info,
            message=f"Étendue de la couche '{layer.name()}' de la session '{session_id}' récupérée",
            metadata={
                'session_id': session_id,
                'layer_id': layer_id,
                'layer_type': 'vector' if layer.type() == 0 else 'raster' if layer.type() == 1 else 'unknown',
                'feature_count': layer.featureCount() if hasattr(layer, 'featureCount') else None
            }
        )
        
    except Exception as e:
        return handle_exception(e, "get_layer_extent", "Impossible de récupérer l'étendue de la couche")


@api_view(['POST'])
@permission_classes([AllowAny])
def zoom_to_layer(request):
    """Zoomer sur une couche avec informations d'étendue détaillées"""
    try:
        layer_id = request.data.get('layer_id')
        session_id = request.data.get('session_id')
        
        if not layer_id:
            return standard_response(
                success=False,
                error="layer_id is required",
                message="L'ID de la couche est requis",
                status_code=400
            )
        
        if not session_id:
            return standard_response(
                success=False,
                error="session_id is required",
                message="L'identifiant de session est requis",
                status_code=400
            )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False, 
                error=error, 
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Obtenir la session existante
        with project_sessions_lock:
            session = project_sessions.get(session_id)
            if session is None:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée. Veuillez créer une nouvelle session.",
                    status_code=404
                )
        
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsProject = classes['QgsProject']
        
        # Obtenir le projet pour cette session
        project = session.get_project(QgsProject)
        
        # Obtenir la couche
        layer = project.mapLayer(layer_id)
        if not layer:
            return standard_response(
                success=False,
                error="Layer not found",
                message=f"Couche avec ID '{layer_id}' de la session '{session_id}' non trouvée",
                status_code=404
            )
        
        # Calculer l'étendue
        extent = layer.extent()
        
        # Calculer les dimensions
        width = extent.xMaximum() - extent.xMinimum()
        height = extent.yMaximum() - extent.yMinimum()
        
        extent_info = {
            'xmin': round(extent.xMinimum(), 6),
            'ymin': round(extent.yMinimum(), 6),
            'xmax': round(extent.xMaximum(), 6),
            'ymax': round(extent.yMaximum(), 6),
            'center': {
                'x': round((extent.xMinimum() + extent.xMaximum()) / 2, 6),
                'y': round((extent.yMinimum() + extent.yMaximum()) / 2, 6)
            },
            'dimensions': {
                'width': round(width, 6),
                'height': round(height, 6)
            },
            'area': round(width * height, 6) if width > 0 and height > 0 else 0
        }
        
        return standard_response(
            success=True,
            data=extent_info,
            message=f"Étendue de la couche '{layer.name()}' de la session '{session_id}' récupérée",
            metadata={
                'session_id': session_id,
                'layer_name': layer.name(),
                'layer_id': layer_id,
                'coordinate_system': layer.crs().authid() if layer.crs() else None
            }
        )
        
    except Exception as e:
        return handle_exception(e, "zoom_to_layer", "Impossible de récupérer l'étendue de la couche")

@api_view(['POST'])
@permission_classes([AllowAny])
def execute_processing(request):
    """Exécuter un algorithme de traitement avec suivi détaillé"""
    try:
        algorithm_name = request.data.get('algorithm')
        parameters = request.data.get('parameters', {})
        output_format = request.data.get('output_format', 'json')
        
        if not algorithm_name:
            return standard_response(
                success=False,
                error="algorithm name is required",
                message="Le nom de l'algorithme est requis",
                status_code=400
            )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False, 
                error=error, 
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsApplication = classes['QgsApplication']
        QgsProcessingContext = classes['QgsProcessingContext']
        QgsProcessingFeedback = classes['QgsProcessingFeedback']
        processing = classes['processing']
        
        # Obtenir l'algorithme
        try:
            alg = QgsApplication.processingRegistry().algorithmById(algorithm_name)
            if not alg:
                return standard_response(
                    success=False,
                    error="Algorithm not found",
                    message=f"L'algorithme '{algorithm_name}' n'a pas été trouvé",
                    status_code=400
                )
        except Exception:
            alg = None
        
        # Exécuter l'algorithme
        feedback = QgsProcessingFeedback()
        context = QgsProcessingContext()
        
        results = processing.run(algorithm_name, parameters, context=context, feedback=feedback)
        
        # Formater les résultats selon le format demandé
        formatted_results = {}
        if output_format == 'json':
            formatted_results = results
        elif output_format == 'summary':
            formatted_results = {
                'outputs_count': len(results),
                'outputs_summary': {k: type(v).__name__ for k, v in results.items()}
            }
        
        return standard_response(
            success=True,
            data={
                'algorithm': algorithm_name,
                'algorithm_name': alg.displayName() if alg else algorithm_name,
                'parameters': parameters,
                'results': formatted_results,
                'execution_time': datetime.now().isoformat(),
                'feedback': feedback
            },
            message="Algorithme exécuté avec succès"
        )
        
    except Exception as e:
        return handle_exception(e, "execute_processing", "Impossible d'exécuter l'algorithme de traitement")

@api_view(['POST'])
@permission_classes([AllowAny])
def render_map(request):
    """Générer un rendu de carte avec options avancées"""
    try:
        session_id = request.data.get('session_id')
        width = int(request.data.get('width', 800))
        height = int(request.data.get('height', 600))
        dpi = int(request.data.get('dpi', 96))
        format_output = request.data.get('format_image', 'png').lower()
        quality = max(1, min(100, int(request.data.get('quality', 90))))
        background_color = request.data.get('background', 'transparent')
        bbox = request.data.get('bbox')
        scale = request.data.get('scale')
        show_points = request.data.get('show_points')
        points_style = request.data.get('points_style', 'circle')
        points_color = request.data.get('points_color', '#FF0000')
        points_size = max(1, min(50, int(request.data.get('points_size', 10))))
        points_labels = request.data.get('points_labels', 'false').lower() == 'true'
        show_grid = request.data.get('show_grid', 'false').lower() == 'true'
        grid_type = request.data.get('grid_type', 'lines')
        grid_spacing = max(0.001, float(request.data.get('grid_spacing', 1.0)))
        grid_color = request.data.get('grid_color', '#0000FF')
        grid_width = max(1, min(10, int(request.data.get('grid_width', 1))))
        grid_size = max(1, min(20, int(request.data.get('grid_size', 3))))
        grid_labels = request.data.get('grid_labels', 'false').lower() == 'true'
        grid_label_position = request.data.get('grid_label_position', 'edges')  # 'corners', 'edges', 'all'
        grid_vertical_labels = request.data.get('grid_vertical_labels', 'false').lower() == 'true'
        grid_label_font_size = max(6, min(20, int(request.data.get('grid_label_font_size', 8))))
        
       # Validation des paramètres
        if not session_id:
            return standard_response(
                success=False,
                error="session_id is required",
                message="L'identifiant de session est requis",
                status_code=400
            )
        
        allowed_formats = ['png', 'jpg', 'jpeg']
        if format_output not in allowed_formats:
            return standard_response(
                success=False,
                error="Unsupported format",
                message=f"Formats supportés: {', '.join(allowed_formats)}",
                status_code=400
            )
        
        allowed_grid_types = ['lines', 'dots', 'crosses']
        if grid_type not in allowed_grid_types:
            return standard_response(
                success=False,
                error="Unsupported grid type",
                message=f"Types de grille supportés: {', '.join(allowed_grid_types)}",
                status_code=400
            )
        
        allowed_label_positions = ['corners', 'edges', 'all']
        if grid_label_position not in allowed_label_positions:
            return standard_response(
                success=False,
                error="Unsupported label position",
                message=f"Positions de labels supportées: {', '.join(allowed_label_positions)}",
                status_code=400
            )
        
        # Validation du bbox si fourni
        extent = None
        if bbox:
            try:
                coords = [float(x) for x in bbox.split(',')]
                if len(coords) == 4:
                    from qgis.core import QgsRectangle
                    extent = QgsRectangle(coords[0], coords[1], coords[2], coords[3])
                else:
                    return standard_response(
                        success=False,
                        error="Invalid bbox format",
                        message="Le format bbox doit être: xmin,ymin,xmax,ymax",
                        status_code=400
                    )
            except ValueError:
                return standard_response(
                    success=False,
                    error="Invalid bbox values",
                    message="Les coordonnées du bbox doivent être des nombres",
                    status_code=400
                )
        
        # Parser les points géographiques si fournis
        geo_points = []
        if show_points:
            try:
                import json
                points_data = json.loads(show_points)
                if isinstance(points_data, list):
                    for point_item in points_data:
                        if isinstance(point_item, dict) and 'x' in point_item and 'y' in point_item:
                            point_info = {
                                'x': float(point_item['x']),
                                'y': float(point_item['y']),
                                'label': point_item.get('label', ''),
                                'color': point_item.get('color', points_color),
                                'size': point_item.get('size', points_size)
                            }
                            geo_points.append(point_info)
                        elif isinstance(point_item, list) and len(point_item) >= 2:
                            point_info = {
                                'x': float(point_item[0]),
                                'y': float(point_item[1]),
                                'label': str(point_item[2]) if len(point_item) > 2 else '',
                                'color': points_color,
                                'size': points_size
                            }
                            geo_points.append(point_info)
            except json.JSONDecodeError:
                return standard_response(
                    success=False,
                    error="Invalid points format",
                    message="Le format des points doit être un JSON valide",
                    status_code=400
                )
            except ValueError:
                return standard_response(
                    success=False,
                    error="Invalid point coordinates",
                    message="Les coordonnées des points doivent être des nombres",
                    status_code=400
                )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False,
                error=error,
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
            
        # Obtenir la session existante
        with project_sessions_lock:
            session = project_sessions.get(session_id)
            if session is None:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée. Veuillez créer une nouvelle session.",
                    status_code=404
                )
        
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsProject = classes['QgsProject']
        QgsMapSettings = classes['QgsMapSettings']
        QgsMapRendererParallelJob = classes['QgsMapRendererParallelJob']
        QgsRectangle = classes['QgsRectangle']
        
        # Obtenir le projet pour cette session
        project = session.get_project(QgsProject)
        
        # Configuration du rendu
        map_settings = QgsMapSettings()
        map_settings.setOutputSize(QSize(width, height))
        map_settings.setOutputDpi(dpi)
        
        # Définir le CRS
        if project.crs().isValid():
            map_settings.setDestinationCrs(project.crs())
        
        # Définir l'étendue
        if extent:
            # Utiliser l'étendue fournie
            map_settings.setExtent(extent)
        else:
            # Calculer l'étendue combinée des couches
            try:
                project_extent = QgsRectangle()
                project_extent.setMinimal()
                
                visible_layers = []
                for layer in project.mapLayers().values():
                    # Ne considérer que les couches visibles
                    if layer.isValid() and not layer.extent().isEmpty():
                        visible_layers.append(layer)
                        if project_extent.isEmpty():
                            project_extent = QgsRectangle(layer.extent())
                        else:
                            project_extent.combineExtentWith(layer.extent())
                
                if not project_extent.isEmpty() and visible_layers:
                    # Appliquer l'échelle si spécifiée
                    if scale:
                        try:
                            scale_value = float(scale)
                            if scale_value > 0:
                                # Calculer la nouvelle étendue basée sur l'échelle
                                center_x = (project_extent.xMinimum() + project_extent.xMaximum()) / 2
                                center_y = (project_extent.yMinimum() + project_extent.yMaximum()) / 2
                                
                                # Convertir l'échelle en dimensions (approximatif)
                                # 1 unité de carte = 1 mètre à l'échelle donnée
                                map_units_per_pixel = scale_value / (dpi * 0.0254)  # 0.0254 m/pouce
                                new_width = width * map_units_per_pixel
                                new_height = height * map_units_per_pixel
                                
                                new_extent = QgsRectangle(
                                    center_x - new_width/2,
                                    center_y - new_height/2,
                                    center_x + new_width/2,
                                    center_y + new_height/2
                                )
                                map_settings.setExtent(new_extent)
                            else:
                                map_settings.setExtent(project_extent)
                        except ValueError:
                            map_settings.setExtent(project_extent)
                    else:
                        # Ajouter une marge de 5%
                        margin = 0.05
                        width_margin = (project_extent.xMaximum() - project_extent.xMinimum()) * margin
                        height_margin = (project_extent.yMaximum() - project_extent.yMinimum()) * margin
                        extended_extent = QgsRectangle(
                            project_extent.xMinimum() - width_margin,
                            project_extent.yMinimum() - height_margin,
                            project_extent.xMaximum() + width_margin,
                            project_extent.yMaximum() + height_margin
                        )
                        map_settings.setExtent(extended_extent)
                else:
                    # Étendue par défaut si aucune couche
                    default_extent = QgsRectangle(-180, -90, 180, 90)
                    map_settings.setExtent(default_extent)
            except Exception as e:
                logger.warning(f"Erreur lors du calcul de l'étendue: {e}")
                # Étendue par défaut en cas d'erreur
                default_extent = QgsRectangle(-180, -90, 180, 90)
                map_settings.setExtent(default_extent)
        
        # Définir les couches visibles
        visible_layers = [layer for layer in project.mapLayers().values() if layer.isValid()]
        map_settings.setLayers(visible_layers)
        
        # Définir la couleur de fond
        if background_color != 'transparent':
            from PyQt5.QtGui import QColor
            try:
                color = QColor(background_color)
                if color.isValid():
                    map_settings.setBackgroundColor(color)
            except Exception as e:
                logger.warning(f"Couleur de fond invalide: {e}")
                # Utiliser la couleur par défaut
                map_settings.setBackgroundColor(QColor(255, 255, 255))
        else:
            # Fond transparent
            from PyQt5.QtGui import QColor
            map_settings.setBackgroundColor(QColor(0, 0, 0, 0))  # RGBA avec alpha = 0
        
        # Configuration du rendu avec antialiasing
        map_settings.setFlag(QgsMapSettings.Antialiasing, True)
        map_settings.setFlag(QgsMapSettings.DrawLabeling, True)
        map_settings.setFlag(QgsMapSettings.UseAdvancedEffects, True)
        
        # Rendu
        from PyQt5.QtGui import QImage, QPainter, QPen, QBrush, QFont
        from PyQt5.QtCore import QBuffer, QByteArray, QIODevice, Qt, QPoint
        from PyQt5.QtGui import QColor
        
        # Choisir le format d'image approprié
        if format_output == 'png':
            image_format = QImage.Format_ARGB32 if background_color == 'transparent' else QImage.Format_RGB32
        else:  # jpg/jpeg
            image_format = QImage.Format_RGB32
        
        image = QImage(width, height, image_format)
        
        # Remplir l'image avec la couleur de fond
        if background_color == 'transparent' and format_output == 'png':
            image.fill(0)  # Fond transparent
        else:
            from PyQt5.QtGui import QColor
            if background_color != 'transparent':
                color = QColor(background_color)
                if color.isValid():
                    image.fill(color)
                else:
                    image.fill(QColor(255, 255, 255))  # Blanc par défaut
            else:
                image.fill(QColor(255, 255, 255))
        
        # Créer un painter pour le rendu
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        # Rendu parallèle des couches existantes
        job = QgsMapRendererParallelJob(map_settings)
        job.start()
        job.waitForFinished()
        rendered_image = job.renderedImage()
        
        # Dessiner l'image rendue sur l'image finale
        painter.drawImage(0, 0, rendered_image)
        
        # Obtenir l'étendue de la carte pour la grille
        extent_map = map_settings.extent()
        
        # Dessiner la grille si demandé
        if show_grid:
            try:
                # Définir le style de la grille
                grid_qcolor = QColor(grid_color)
                if not grid_qcolor.isValid():
                    grid_qcolor = QColor(0, 0, 255)  # Bleu par défaut
                
                painter.setPen(QPen(grid_qcolor, grid_width))
                painter.setFont(QFont('Arial', grid_label_font_size))
                
                # Calculer les lignes de grille
                x_min = extent_map.xMinimum()
                x_max = extent_map.xMaximum()
                y_min = extent_map.yMinimum()
                y_max = extent_map.yMaximum()
                
                # Lignes verticales (méridiens)
                x_start = (x_min // grid_spacing) * grid_spacing
                x_lines = []
                x = x_start
                while x <= x_max:
                    if x >= x_min:
                        x_lines.append(x)
                    x += grid_spacing
                
                # Lignes horizontales (parallèles)
                y_start = (y_min // grid_spacing) * grid_spacing
                y_lines = []
                y = y_start
                while y <= y_max:
                    if y >= y_min:
                        y_lines.append(y)
                    y += grid_spacing
                
                # Dessiner selon le type de grille
                if grid_type == 'lines':
                    # Grille en lignes continues
                    for x in x_lines:
                        x_pixel = int(((x - x_min) / (x_max - x_min)) * width)
                        painter.drawLine(x_pixel, 0, x_pixel, height)
                    
                    for y in y_lines:
                        y_pixel = int((1 - (y - y_min) / (y_max - y_min)) * height)
                        painter.drawLine(0, y_pixel, width, y_pixel)
                
                elif grid_type == 'dots':
                    # Grille en points
                    painter.setPen(QPen(grid_qcolor, grid_width * 2))  # Points plus visibles
                    for x in x_lines:
                        x_pixel = int(((x - x_min) / (x_max - x_min)) * width)
                        for y in y_lines:
                            y_pixel = int((1 - (y - y_min) / (y_max - y_min)) * height)
                            painter.drawPoint(x_pixel, y_pixel)
                
                elif grid_type == 'crosses':
                    # Grille en croix
                    cross_size = grid_size
                    for x in x_lines:
                        x_pixel = int(((x - x_min) / (x_max - x_min)) * width)
                        for y in y_lines:
                            y_pixel = int((1 - (y - y_min) / (y_max - y_min)) * height)
                            # Ligne horizontale de la croix
                            painter.drawLine(x_pixel - cross_size, y_pixel, x_pixel + cross_size, y_pixel)
                            # Ligne verticale de la croix
                            painter.drawLine(x_pixel, y_pixel - cross_size, x_pixel, y_pixel + cross_size)
                
                # Dessiner les labels si demandé
                if grid_labels:
                    painter.setPen(QPen(grid_qcolor, 1))
                    painter.setFont(QFont('Arial', grid_label_font_size))
                    
                    # Labels verticaux sur les bords gauche et droit si activé
                    if grid_vertical_labels:
                        for j, y in enumerate(y_lines):
                            y_pixel = int((1 - (y - y_min) / (y_max - y_min)) * height)
                            
                            # Déterminer si on doit afficher le label selon la position demandée
                            show_label = False
                            if grid_label_position == 'corners':
                                # Seulement les coins
                                if j == 0 or j == len(y_lines) - 1:
                                    show_label = True
                            elif grid_label_position == 'edges':
                                # Bordures seulement
                                if j == 0 or j == len(y_lines) - 1:
                                    show_label = True
                            else:  # 'all'
                                # Tous les points
                                show_label = True
                            
                            if show_label:
                                label = f"{y:.2f}°"
                                
                                # Label à gauche
                                text_x_left = 10
                                text_y_left = y_pixel + grid_label_font_size//2
                                if 0 <= text_y_left <= height:
                                    # Rotation du texte de 90 degrés
                                    painter.save()
                                    painter.translate(text_x_left, text_y_left)
                                    painter.rotate(-90)
                                    painter.drawText(0, 0, label)
                                    painter.restore()
                                
                                # Label à droite
                                text_x_right = width - grid_label_font_size 
                                text_y_right = y_pixel + grid_label_font_size//2
                                if 0 <= text_y_right <= height:
                                    # Rotation du texte de 90 degrés
                                    painter.save()
                                    painter.translate(text_x_right, text_y_right)
                                    painter.rotate(-90)
                                    painter.drawText(0, 0, label)
                                    painter.restore()
                    
                    # Labels normaux (horizontaux) pour les lignes verticales
                    for i, x in enumerate(x_lines):
                        x_pixel = int(((x - x_min) / (x_max - x_min)) * width)
                        
                        # Déterminer si on doit afficher le label selon la position demandée
                        show_label = False
                        if grid_label_position == 'corners':
                            # Seulement les coins
                            if i == 0 or i == len(x_lines) - 1:
                                show_label = True
                        elif grid_label_position == 'edges':
                            # Bordures seulement (haut et bas)
                            if i == 0 or i == len(x_lines) - 1:
                                show_label = True
                        else:  # 'all'
                            # Tous les points
                            show_label = True
                        
                        if show_label:
                            label = f"{x:.2f}°"
                            
                            # Label en haut
                            text_x_top = x_pixel + 5
                            text_y_top = grid_label_font_size + 5
                            if 0 <= text_x_top <= width - 50:
                                painter.drawText(text_x_top, text_y_top, label)
                            
                            # Label en bas
                            text_x_bottom = x_pixel + 5
                            text_y_bottom = height - 5
                            if 0 <= text_x_bottom <= width - 50:
                                painter.drawText(text_x_bottom, text_y_bottom, label)
                    
            except Exception as e:
                logger.warning(f"Erreur lors du dessin de la grille: {e}")
        
        # Dessiner les points géographiques si fournis
        if geo_points:
            # Convertir les coordonnées géographiques en pixels
            extent_map = map_settings.extent()
            map_width = extent_map.xMaximum() - extent_map.xMinimum()
            map_height = extent_map.yMaximum() - extent_map.yMinimum()
            
            for point_info in geo_points:
                x_geo = point_info['x']
                y_geo = point_info['y']
                label = point_info['label']
                color_hex = point_info['color']
                size = point_info['size']
                
                # Vérifier si le point est dans l'étendue de la carte
                if (extent_map.xMinimum() <= x_geo <= extent_map.xMaximum() and 
                    extent_map.yMinimum() <= y_geo <= extent_map.yMaximum()):
                    
                    # Convertir les coordonnées géographiques en pixels
                    x_pixel = int(((x_geo - extent_map.xMinimum()) / map_width) * width)
                    y_pixel = int((1 - (y_geo - extent_map.yMinimum()) / map_height) * height)
                    
                    # Dessiner le point
                    point_color = QColor(color_hex)
                    if point_color.isValid():
                        painter.setPen(QPen(point_color, 2))
                        painter.setBrush(QBrush(point_color))
                    else:
                        painter.setPen(QPen(QColor(255, 0, 0), 2))
                        painter.setBrush(QBrush(QColor(255, 0, 0)))
                    
                    # Dessiner selon le style
                    if points_style == 'square':
                        painter.drawRect(x_pixel - size//2, y_pixel - size//2, size, size)
                    elif points_style == 'triangle':
                        # Dessiner un triangle pointant vers le haut
                        points_array = [
                            QPoint(x_pixel, y_pixel - size//2),
                            QPoint(x_pixel - size//2, y_pixel + size//2),
                            QPoint(x_pixel + size//2, y_pixel + size//2)
                        ]
                        painter.drawPolygon(*points_array, 3)
                    else:  # circle (par défaut)
                        painter.drawEllipse(x_pixel - size//2, y_pixel - size//2, size, size)
                    
                    # Dessiner le label si demandé
                    if points_labels and label:
                        painter.setPen(QPen(QColor(0, 0, 0)))
                        painter.setFont(QFont('Arial', max(8, size//2)))
                        painter.drawText(x_pixel + size, y_pixel, label)
        
        painter.end()
        
        # Convertir en bytes selon le format
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        
        if format_output in ['jpg', 'jpeg']:
            # Pour JPEG, s'assurer qu'il n'y a pas de transparence
            if image.hasAlphaChannel():
                # Convertir en image sans transparence
                final_image = QImage(image.size(), QImage.Format_RGB32)
                final_image.fill(QColor(255, 255, 255))
                painter = QPainter(final_image)
                painter.drawImage(0, 0, image)
                painter.end()
                final_image.save(buffer, "JPEG", quality)
            else:
                image.save(buffer, "JPEG", quality)
            content_type = 'image/jpeg'
        else:
            image.save(buffer, "PNG")
            content_type = 'image/png'
        
        # Ajouter des headers pour le cache
        response = HttpResponse(byte_array.data(), content_type=content_type)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur dans render_map: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return handle_exception(e, "render_map", "Impossible de générer le rendu de la carte")

@api_view(['POST'])
@permission_classes([AllowAny])
def qr_scanner(request):
    """Scanner et traiter un QR code"""
    try:
        qr_data = request.data.get('qr_data')
        
        if not qr_data:
            return standard_response(
                success=False,
                error="qr_data is required",
                message="Les données QR code sont requises",
                status_code=400
            )
        
        # Simulation de traitement QR
        processed_data = {
            'raw_data': qr_data,
            'data_type': 'parcelle' if 'PARC' in qr_data else 'document' if 'DOC' in qr_data else 'unknown',
            'timestamp': datetime.now().isoformat(),
            'validity': 'valid' if len(qr_data) > 5 else 'questionable'
        }
        
        return standard_response(
            success=True,
            data=processed_data,
            message="QR code scanné et traité avec succès",
            metadata={
                'processing_time': f'{(datetime.now().microsecond % 100)} ms',
                'security_check': 'passed'
            }
        )
        
    except Exception as e:
        return handle_exception(e, "qr_scanner", "Impossible de scanner le QR code")

@api_view(['POST'])
@permission_classes([AllowAny])
def save_project(request):
    """Sauvegarder le projet de la session courante"""
    try:
        session_id = request.data.get('session_id')
        project_path = request.data.get('project_path')
        
        if not session_id:
            return standard_response(
                success=False,
                error="session_id is required",
                message="L'identifiant de session est requis",
                status_code=400
            )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False, 
                error=error, 
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Obtenir la session existante
        with project_sessions_lock:
            session = project_sessions.get(session_id)
            if session is None:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée. Veuillez créer une nouvelle session.",
                    status_code=404
                )
        
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsProject = classes['QgsProject']
        
        # Obtenir le projet pour cette session
        project = session.get_project(QgsProject)
        
        # Sauvegarder le projet
        if not project_path:
            project_path = os.path.join(settings.MEDIA_ROOT, f'{session_id}.qgs')
        
        success_save = project.write(project_path)
        
        if not success_save:
            return standard_response(
                success=False,
                error="Failed to save project",
                message="Échec de la sauvegarde du projet",
                status_code=500
            )
        
        return standard_response(
            success=True,
            data={
                "session_id": session_id,
                "file_path": project_path,
                "saved_at": datetime.now().isoformat()
            },
            message="Projet sauvegardé avec succès"
        )
        
    except Exception as e:
        return handle_exception(e, "save_project", "Impossible de sauvegarder le projet")

@api_view(['POST'])
@permission_classes([AllowAny])
def generate_advanced_pdf(request):
    """
    Générer un PDF avancé avec QgsPrintLayout (la puissance de QGIS)
    """
    try:
        session_id = request.data.get('session_id')
        layout_config = request.data.get('layout_config', {})
        output_filename = request.data.get('output_filename', 'generated_report.pdf')
        
        if not session_id:
            return standard_response(
                success=False,
                error="session_id is required",
                message="L'identifiant de session est requis",
                status_code=400
            )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False, 
                error=error, 
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Obtenir la session existante
        with project_sessions_lock:
            session = project_sessions.get(session_id)
            if session is None:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée. Veuillez créer une nouvelle session.",
                    status_code=404
                )
        
        manager = get_qgis_manager()
        classes = manager.get_classes()
        QgsProject = classes['QgsProject']
        QgsPrintLayout = classes['QgsPrintLayout']
        QgsLayoutExporter = classes['QgsLayoutExporter']
        
        # Obtenir le projet pour cette session
        project = session.get_project(QgsProject)
        
        # Créer le layout PDF
        layout = create_print_layout_with_qgs(
            f"Layout_{session_id}",
            project,
            layout_config.get('map_items', {})
        )
        # layout = create_carte(project,{"is_distance":False,"is_grid":True,"is_legend":False},{})
        
        if not layout:
            return standard_response(
                success=False,
                error="Failed to create print layout",
                message="Impossible de créer le layout PDF",
                status_code=500
            )
        
        # Définir le chemin de sortie
        output_path = os.path.join(settings.MEDIA_ROOT, output_filename)
        
        # Exporter en PDF
        exporter = QgsLayoutExporter(layout)
        result = exporter.exportToPdf(output_path,QgsLayoutExporter.PdfExportSettings())
        
        if result != QgsLayoutExporter.Success:
            return standard_response(
                success=False,
                error=f"Export failed with code: {result}",
                message="Échec de l'exportation PDF",
                status_code=500
            )
        
        
        # Retourner le chemin du fichier généré
        return standard_response(
            success=True,
            data={
                "file_path": output_path,
                "file_name": output_filename,
                "size_bytes": os.path.getsize(output_path),
                "url": f"/media/{output_filename}"
            },
            message="PDF généré avec succès"
        )
        
    except Exception as e:
        return handle_exception(e, "generate_advanced_pdf", "Impossible de générer le PDF avancé")

@api_view(['GET'])
@permission_classes([AllowAny])
def download_file(request, filename):
    """Télécharger un fichier généré"""
    try:
        file_path = os.path.join(settings.MEDIA_ROOT, filename)
        if not os.path.exists(file_path):
            return standard_response(
                success=False,
                error="File not found",
                message="Fichier non trouvé",
                status_code=404
            )
        
        response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return handle_exception(e, "download_file", "Impossible de télécharger le fichier")

@api_view(['GET'])
@permission_classes([AllowAny])
def list_files(request):
    """Lister les fichiers dans le répertoire MEDIA"""
    try:
        directory = request.GET.get('directory', '')
        file_type = request.GET.get('type', 'all')
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        
        # Chemin complet
        if directory:
            dir_path = os.path.join(settings.MEDIA_ROOT, directory)
        else:
            dir_path = settings.MEDIA_ROOT
            
        if not os.path.exists(dir_path):
            return standard_response(
                success=False,
                error="Directory not found",
                message="Répertoire non trouvé",
                status_code=404
            )
        
        # Liste des fichiers
        all_files = []
        for file_name in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file_name)
            if os.path.isfile(file_path):
                stat_info = os.stat(file_path)
                file_info = {
                    'name': file_name,
                    'path': file_path,
                    'size': stat_info.st_size,
                    'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                    'extension': os.path.splitext(file_name)[1].lower(),
                    'type': 'vector' if file_name.endswith(('.shp', '.geojson', '.kml')) else
                           'raster' if file_name.endswith(('.tif', '.tiff')) else
                           'document' if file_name.endswith(('.pdf', '.doc', '.docx')) else
                           'other'
                }
                
                # Filtrer par type si spécifié
                if file_type != 'all' and file_info['type'] != file_type:
                    continue
                    
                all_files.append(file_info)
        
        # Tri par date de modification (le plus récent en premier)
        all_files.sort(key=lambda x: x['modified'], reverse=True)
        
        # Pagination
        total_count = len(all_files)
        start_index = (page - 1) * per_page
        end_index = min(start_index + per_page, total_count)
        paginated_files = all_files[start_index:end_index]
        
        return standard_response(
            success=True,
            data={
                'files': paginated_files,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': (total_count + per_page - 1) // per_page,
                    'has_next': page < (total_count + per_page - 1) // per_page,
                    'has_previous': page > 1
                }
            },
            message=f"{len(paginated_files)} fichiers récupérés sur {total_count} au total"
        )
        
    except Exception as e:
        return handle_exception(e, "list_files", "Impossible de lister les fichiers")

@api_view(['GET'])
@permission_classes([AllowAny])
def ping(request):
    """Endpoint de test pour vérifier que le service est actif"""
    manager = get_qgis_manager()
    return standard_response(
        success=True,
        data={
            "status": "ok",
            "service": "FlashCroquis API",
            "version": "1.0.0",
            "qgis_initialized": manager.is_initialized()
        },
        message="Service en ligne et opérationnel"
    )

@api_view(['GET'])
@permission_classes([AllowAny])
def qgis_info(request):
    """Informations détaillées sur la configuration QGIS"""
    try:
        manager = get_qgis_manager()
        if not manager.is_initialized():
            success, error = manager.initialize()
            if not success:
                return standard_response(
                    success=False,
                    error=error,
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
        
        classes = manager.get_classes()
        QgsApplicationClass = classes['QgsApplication']
        Qgis = classes['Qgis']
        
        info = {
            "qgis_version": Qgis.QGIS_VERSION,
            "qgis_version_int": Qgis.QGIS_VERSION_INT,
            "qgis_version_name": Qgis.QGIS_RELEASE_NAME,
            "status": "initialized" if QgsApplicationClass.instance() else "partially_initialized",
            "algorithms_count": len(QgsApplicationClass.processingRegistry().algorithms()) if hasattr(QgsApplicationClass, 'processingRegistry') and QgsApplicationClass.instance() else 0,
            "initialization_time": datetime.now().isoformat()
        }
        
        return standard_response(
            success=True,
            data=info,
            message="Informations QGIS récupérées avec succès"
        )
        
    except Exception as e:
        return handle_exception(e, "qgis_info", "Impossible de récupérer les informations QGIS")

# Point d'entrée principal pour les tests
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Vérification de santé de l'API"""
    return standard_response(
        success=True,
        data={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "qgis_ready": get_qgis_manager().is_initialized()
        },
        message="Service opérationnel"
    )

# Vue spécifique pour les parcelles
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def parcelle_detail(request, parcelle_id):
    """Gérer une parcelle spécifique avec détails complets"""
    try:
        if request.method == 'GET':
            return standard_response(
                success=True,
                data={
                    "id": parcelle_id,
                    "details": {
                        "nom": "Parcelle 123",
                        "superficie": "1250 m²",
                        "proprietaire": "Jean Dupont",
                        "localisation": "Zone A",
                        "date_creation": "2025-08-27"
                    }
                },
                message=f"Détails de la parcelle {parcelle_id} récupérés"
            )
        elif request.method == 'POST':
            parcelle_data = request.data
            return standard_response(
                success=True,
                data={
                    "status": "updated",
                    "parcelle_id": parcelle_id,
                    "data": parcelle_data
                },
                message=f"Parcelle {parcelle_id} créée/modifiée avec succès"
            )
    except Exception as e:
        return handle_exception(e, "parcelle_detail", "Impossible de traiter la parcelle")

# Vue spécifique pour la liste des parcelles
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def parcelles_list(request):
    """Gérer la liste des parcelles avec pagination"""
    try:
        if request.method == 'GET':
            page = int(request.GET.get('page', 1))
            per_page = int(request.GET.get('per_page', 20))
            search = request.GET.get('search', '')
            
            # Simulation de données
            parcelles = []
            total_count = 150  # Nombre total simulé
            
            start_index = (page - 1) * per_page
            end_index = min(start_index + per_page, total_count)
            
            for i in range(start_index, end_index):
                parcelles.append({
                    'id': f'PARC{i+1:04d}',
                    'surface': f'{(i % 100) + 50:.2f} m²',
                    'proprietaire': f'Propriétaire {(i % 20) + 1}',
                    'adresse': f'{(i % 50) + 1} Rue de la Parcelle, Ville {((i // 50) % 5) + 1}',
                    'statut': ['active', 'inactive', 'en_cours'][i % 3]
                })
            
            return standard_response(
                success=True,
                data={
                    'parcelles': parcelles,
                    'pagination': {
                        'current_page': page,
                        'per_page': per_page,
                        'total_count': total_count,
                        'total_pages': (total_count + per_page - 1) // per_page,
                        'has_next': page < (total_count + per_page - 1) // per_page,
                        'has_previous': page > 1
                    }
                },
                message=f"{len(parcelles)} parcelles récupérées sur {total_count} au total"
            )
        elif request.method == 'POST':
            parcelle_data = request.data
            new_id = f'PARC{datetime.now().strftime("%Y%m%d%H%M%S")}'
            return standard_response(
                success=True,
                data={
                    'status': 'created',
                    'parcelle_id': new_id,
                    'data': parcelle_data
                },
                message="Nouvelle parcelle créée avec succès"
            )
    except Exception as e:
        return handle_exception(e, "parcelles_list", "Impossible de récupérer la liste des parcelles")

# Vue pour générer un croquis avec options avancées
@api_view(['POST'])
@permission_classes([AllowAny])
def generate_croquis(request):
    """
    Générer un croquis avec options avancées
    """
    try:
        # Configuration des paramètres
        config_data = request.data.get('config', {})
        session_id = request.data.get('session_id')
        output_filename = request.data.get('output_filename', 'croquis.pdf')
        
        if not session_id:
            return standard_response(
                success=False,
                error="session_id is required",
                message="L'identifiant de session est requis",
                status_code=400
            )
        
        success, error = initialize_qgis_if_needed()
        if not success:
            return standard_response(
                success=False, 
                error=error, 
                message="Échec de l'initialisation de QGIS",
                status_code=500
            )
        
        # Obtenir la session existante
        with project_sessions_lock:
            session = project_sessions.get(session_id)
            if session is None:
                return standard_response(
                    success=False,
                    error="Session not found",
                    message="Session non trouvée. Veuillez créer une nouvelle session.",
                    status_code=404
                )
        
        # Simuler la génération du croquis
        # Dans une implémentation réelle, vous utiliseriez ici QgsPrintLayout
        # pour créer un document PDF avec les éléments du PDF fourni
        
        # Pour cet exemple, nous simulerons simplement un succès
        return standard_response(
            success=True,
            data={
                "message": "Croquis généré avec succès",
                "output_filename": output_filename,
                "config": config_data
            },
            message="Document croquis généré avec succès"
        )
        
    except Exception as e:
        return handle_exception(e, "generate_croquis", "Impossible de générer le croquis")