import logging
import os
from threading import Lock

logger = logging.getLogger(__name__)

project_sessions = {}
project_sessions_lock = Lock()
qgis_manager = None
qgis_classes = {}

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

