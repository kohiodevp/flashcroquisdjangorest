import os
from rest_framework import viewsets, status, mixins, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from .models import ProjectSession, Layer, ProcessingJob, GeneratedFile
from .serializers import (
    ProjectSessionSerializer, LayerSerializer, ProcessingJobSerializer, 
    GeneratedFileSerializer, LayerFeatureSerializer, VectorLayerAddSerializer,
    RasterLayerAddSerializer, MapRenderSerializer, PDFGenerateSerializer, QRScanSerializer
)
from .qgis_manager import get_qgis_manager, initialize_qgis_if_needed
from .utils import standard_response, handle_exception, format_layer_info, format_project_info
import logging
from datetime import datetime
from . import settings

logger = logging.getLogger(__name__)

# class ProjectSessionViewSet(viewsets.GenericViewSet,
#                            mixins.CreateModelMixin,
#                            mixins.RetrieveModelMixin):
#     queryset = ProjectSession.objects.all()
#     serializer_class = ProjectSessionSerializer
#     permission_classes = [AllowAny]
#     lookup_field = 'session_id'
    
#     def create(self, request):
#         """Créer un nouveau projet QGIS avec session persistante"""
#         try:
#             project_title = request.data.get('title', 'Nouveau Projet')
#             crs_id = request.data.get('crs', 'EPSG:4326')
            
#             success, error = initialize_qgis_if_needed()
#             if not success:
#                 return standard_response(
#                     success=False, 
#                     error=error, 
#                     message="Échec de l'initialisation de QGIS",
#                     status_code=500
#                 )
            
#             # Créer une nouvelle session en base de données
#             session = ProjectSession.objects.create(
#                 project_title=project_title,
#                 project_crs=crs_id
#             )
            
#             manager = get_qgis_manager()
#             classes = manager.get_classes()
#             QgsProject = classes['QgsProject']
            
#             # Créer le projet QGIS
#             qgis_project = QgsProject()
#             qgis_project.setTitle(project_title)

#             # Créer le répertoire de projets s'il n'existe pas
#             projects_dir = os.path.join(settings.MEDIA_ROOT, 'projects')
#             os.makedirs(projects_dir, exist_ok=True)
            
#             # Sauvegarder le projet
#             project_filename = f'{session.session_id}.qgs'
#             project_path = os.path.join(projects_dir, project_filename)
#             success_save = qgis_project.write(project_path)
            
#             if not success_save:
#                 session.delete()
#                 return standard_response(
#                     success=False,
#                     error="Failed to save project",
#                     message="Impossible de sauvegarder le projet",
#                     status_code=500
#                 )
            
#             session.project_file = project_path
#             session.save()
            
#             return standard_response(
#                 success=True,
#                 data=ProjectSessionSerializer(session).data,
#                 message="Projet créé avec succès"
#             )
            
#         except Exception as e:
#             return handle_exception(e, "create_project", "Impossible de créer le projet")
    
#     def retrieve(self, request, session_id=None):
#         """Obtenir les informations détaillées du projet courant de la session"""
#         try:
#             session = get_object_or_404(ProjectSession, session_id=session_id)
            
#             success, error = initialize_qgis_if_needed()
#             if not success:
#                 return standard_response(
#                     success=False, 
#                     error=error, 
#                     message="Échec de l'initialisation de QGIS",
#                     status_code=500
#                 )
            
#             manager = get_qgis_manager()
#             classes = manager.get_classes()
#             QgsProject = classes['QgsProject']
            
#             # Charger le projet QGIS
#             qgis_project = QgsProject()
#             success_load = qgis_project.read(session.project_file.path)
            
#             if not success_load:
#                 return standard_response(
#                     success=False,
#                     error="Failed to load project",
#                     message="Impossible de charger le projet",
#                     status_code=500
#                 )
            
#             # Mettre à jour les informations de session
#             session_data = ProjectSessionSerializer(session).data
#             session_data['project_info'] = format_project_info(qgis_project)
            
#             return standard_response(
#                 success=True,
#                 data=session_data,
#                 message="Informations du projet récupérées"
#             )
            
#         except Exception as e:
#             return handle_exception(e, "project_info", "Impossible de récupérer les informations du projet")
class ProjectSessionViewSet(viewsets.ModelViewSet):
    queryset = ProjectSession.objects.all()
    serializer_class = ProjectSessionSerializer
    
class LayerViewSet(viewsets.GenericViewSet,
                  mixins.ListModelMixin):
    queryset = Layer.objects.all()
    serializer_class = LayerSerializer
    permission_classes = [AllowAny]
    
    def list(self, request):
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
            
            session = get_object_or_404(ProjectSession, session_id=session_id)
            layers = Layer.objects.filter(session=session)
            
            return standard_response(
                success=True,
                data=LayerSerializer(layers, many=True).data,
                message=f"{layers.count()} couches récupérées"
            )
            
        except Exception as e:
            return handle_exception(e, "get_layers", "Impossible de récupérer la liste des couches")
    
    @action(detail=False, methods=['post'], serializer_class=VectorLayerAddSerializer)
    def add_vector(self, request):
        """Ajouter une couche vectorielle à la session courante"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            session = get_object_or_404(ProjectSession, session_id=data['session_id'])
            
            # Logique d'ajout de couche vectorielle (similaire à l'original)
            # ... (le code original d'add_vector_layer adapté)
            
            # Après ajout réussi, créer l'enregistrement Layer
            layer = Layer.objects.create(
                session=session,
                layer_id="generated_id",  # À remplacer par l'ID réel
                name=data['layer_name'],
                # ... autres champs
            )
            
            return standard_response(
                success=True,
                data=LayerSerializer(layer).data,
                message=f"Couche vectorielle '{data['layer_name']}' ajoutée avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "add_vector_layer", "Impossible d'ajouter la couche vectorielle")
    
    @action(detail=False, methods=['post'], serializer_class=RasterLayerAddSerializer)
    def add_raster(self, request):
        """Ajouter une couche raster à la session"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            session = get_object_or_404(ProjectSession, session_id=data['session_id'])
            
            # Logique d'ajout de couche raster (similaire à l'original)
            # ... (le code original d'add_raster_layer adapté)
            
            # Après ajout réussi, créer l'enregistrement Layer
            layer = Layer.objects.create(
                session=session,
                layer_id="generated_id",  # À remplacer par l'ID réel
                name=data['layer_name'],
                # ... autres champs
            )
            
            return standard_response(
                success=True,
                data=LayerSerializer(layer).data,
                message=f"Couche raster '{data['layer_name']}' ajoutée avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "add_raster_layer", "Impossible d'ajouter la couche raster")
    
    @action(detail=True, methods=['get'], serializer_class=LayerFeatureSerializer)
    def features(self, request, pk=None):
        """Obtenir les caractéristiques d'une couche avec pagination"""
        try:
            serializer = self.get_serializer(data={
                'layer_id': pk,
                'session_id': request.GET.get('session_id'),
                'offset': request.GET.get('offset', 0),
                'limit': request.GET.get('limit', 100)
            })
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            session = get_object_or_404(ProjectSession, session_id=data['session_id'])
            layer = get_object_or_404(Layer, session=session, layer_id=data['layer_id'])
            
            # Logique de récupération des features (similaire à l'original)
            # ... (le code original de get_layer_features adapté)
            
            return standard_response(
                success=True,
                data={},  # Remplacer par les données réelles
                message="Features récupérés avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "get_layer_features", "Impossible de récupérer les features de la couche")

class ProcessingViewSet(viewsets.GenericViewSet):
    queryset = ProcessingJob.objects.all()
    serializer_class = ProcessingJobSerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def execute(self, request):
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
            
            session_id = parameters.get('session_id')
            if not session_id:
                return standard_response(
                    success=False,
                    error="session_id is required",
                    message="L'identifiant de session est requis",
                    status_code=400
                )
            
            session = get_object_or_404(ProjectSession, session_id=session_id)
            
            # Créer un job de traitement
            job = ProcessingJob.objects.create(
                session=session,
                algorithm=algorithm_name,
                parameters=parameters,
                status='pending'
            )
            
            # Exécuter le traitement (pourrait être fait en arrière-plan avec Celery)
            success, error = initialize_qgis_if_needed()
            if not success:
                job.status = 'failed'
                job.error = error
                job.save()
                
                return standard_response(
                    success=False, 
                    error=error, 
                    message="Échec de l'initialisation de QGIS",
                    status_code=500
                )
            
            # Logique d'exécution du processing (similaire à l'original)
            # ... (le code original de execute_processing adapté)
            
            # Mettre à jour le job
            job.status = 'completed'
            job.result = {}  # Remplacer par le résultat réel
            job.save()
            
            return standard_response(
                success=True,
                data=ProcessingJobSerializer(job).data,
                message="Algorithme exécuté avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "execute_processing", "Impossible d'exécuter l'algorithme de traitement")

class MapViewSet(viewsets.GenericViewSet):
    queryset = GeneratedFile.objects.all()
    serializer_class = GeneratedFileSerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'], serializer_class=MapRenderSerializer)
    def render(self, request):
        """Générer un rendu de carte avec options avancées"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            session = get_object_or_404(ProjectSession, session_id=data['session_id'])
            
            # Logique de rendu de carte (similaire à l'original)
            # ... (le code original de render_map adapté)
            
            # Sauvegarder l'image générée
            generated_file = GeneratedFile.objects.create(
                session=session,
                name=f"map_render_{session.session_id}",
                file_type='image',
                file_path='path/to/generated/image.png',  # Remplacer par le chemin réel
                size=1000,  # Remplacer par la taille réelle
                metadata=data
            )
            
            return standard_response(
                success=True,
                data=GeneratedFileSerializer(generated_file, context={'request': request}).data,
                message="Carte générée avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "render_map", "Impossible de générer le rendu de la carte")
    
    @action(detail=False, methods=['post'], serializer_class=PDFGenerateSerializer)
    def generate_pdf(self, request):
        """Générer un PDF avancé avec QgsPrintLayout"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            session = get_object_or_404(ProjectSession, session_id=data['session_id'])
            
            # Logique de génération PDF (similaire à l'original)
            # ... (le code original de generate_advanced_pdf adapté)
            
            # Sauvegarder le PDF généré
            generated_file = GeneratedFile.objects.create(
                session=session,
                name=data['output_filename'],
                file_type='pdf',
                file_path='path/to/generated/file.pdf',  # Remplacer par le chemin réel
                size=1000,  # Remplacer par la taille réelle
                metadata=data
            )
            
            return standard_response(
                success=True,
                data=GeneratedFileSerializer(generated_file, context={'request': request}).data,
                message="PDF généré avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "generate_advanced_pdf", "Impossible de générer le PDF avancé")

class QRViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = QRScanSerializer
    
    @action(detail=False, methods=['post'])
    def scan(self, request):
        """Scanner et traiter un QR code"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            
            # Logique de traitement QR (similaire à l'original)
            # ... (le code original de qr_scanner adapté)
            
            return standard_response(
                success=True,
                data={},  # Remplacer par les données réelles
                message="QR code scanné et traité avec succès"
            )
            
        except Exception as e:
            return handle_exception(e, "qr_scanner", "Impossible de scanner le QR code")

class HealthCheckViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = serializers.Serializer  # Sérialiseur de base

    @action(detail=False, methods=['get'])
    def ping(self, request):
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
    
    @action(detail=False, methods=['get'])
    def health(self, request):
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