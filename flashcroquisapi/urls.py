from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from . import views

urlpatterns = [
    # Routes de base
    path('ping/', views.ping, name='ping'),
    path('health/', views.health_check, name='health_check'),
    path('qgis-info/', views.qgis_info, name='qgis_info'),
    
    # Gestion des projets
    path('projects/create/', views.create_project, name='create_project'),
    path('projects/load/', views.load_project, name='load_project'),
    path('projects/info/', views.project_info, name='project_info'),
    path('projects/save/', views.save_project, name='save_project'),
    
    # Gestion des couches
    path('layers/list/', views.get_layers, name='get_layers'),
    path('layers/add-vector/', views.add_vector_layer, name='add_vector_layer'),
    path('layers/add-raster/', views.add_raster_layer, name='add_raster_layer'),
    path('layers/remove/', views.remove_layer, name='remove_layer'),
    path('layers/features/<str:layer_id>/', views.get_layer_features, name='get_layer_features'),
    path('layers/extent/<str:layer_id>/', views.get_layer_extent, name='get_layer_extent'),
    path('layers/zoom/<str:layer_id>/', views.zoom_to_layer, name='zoom_to_layer'),
    
    # Traitement QGIS
    path('processing/execute/', views.execute_processing, name='execute_processing'),
    
    # map
    path('map/render/', views.render_map, name='render_map'),
    
    # Génération de documents PDF
    path('documents/generate-pdf/', views.generate_advanced_pdf, name='generate_advanced_pdf'),
    path('documents/download/<str:filename>/', views.download_file, name='download_file'),
    
    # QR Code
    path('qr-scanner/', views.qr_scanner, name='qr_scanner'),
    
    # Parcelles
    path('parcelles/', views.parcelle_detail, name='parcelle_detail'),
    
    # Fichiers
    path('files/list/', views.list_files, name='list_files'),
    path('files/download-file/<str:filename>/', views.download_file, name='download_file'),
    
    # Connexion/QGIS
    # path('qgis/connect/', views.connect_to_qgis, name='connect_to_qgis'),
    # path('qgis/disconnect/', views.disconnect_from_qgis, name='disconnect_from_qgis'),
    
    # Administration
    # path('admin/data/', views.admin_data, name='admin_data'),
    
    # Test
    # path('test/', views.test_endpoint, name='test_endpoint'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)