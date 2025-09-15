from rest_framework import serializers
from .models import ProjectSession, Layer, ProcessingJob, GeneratedFile
from PyQt5.QtCore import QDateTime

class QDateTimeReadOnlyField(serializers.ReadOnlyField):
    """Convertit QDateTime en ISO 8601 pour JSON, lecture seule"""
    def to_representation(self, value):
        if isinstance(value, QDateTime):
            return value.toPython().isoformat()
        elif hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)

class ProjectSessionSerializer(serializers.ModelSerializer):
    created_at = QDateTimeReadOnlyField()
    last_accessed = QDateTimeReadOnlyField()

    class Meta:
        model = ProjectSession
        fields = '__all__'

class LayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Layer
        fields = '__all__'
        read_only_fields = ('created_at',)

class ProcessingJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingJob
        fields = '__all__'
        read_only_fields = ('job_id', 'created_at', 'completed_at')

class GeneratedFileSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = GeneratedFile
        fields = '__all__'
        read_only_fields = ('file_id', 'created_at')
    
    def get_download_url(self, obj):
        request = self.context.get('request')
        if request and obj.file_path:
            return request.build_absolute_uri(obj.file_path.url)
        return None

class LayerFeatureSerializer(serializers.Serializer):
    layer_id = serializers.CharField()
    session_id = serializers.UUIDField()
    offset = serializers.IntegerField(min_value=0, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=1000, default=100)

class VectorLayerAddSerializer(serializers.Serializer):
    data_source = serializers.CharField()
    layer_name = serializers.CharField(default="Couche Vectorielle")
    session_id = serializers.UUIDField()
    is_parcelle = serializers.BooleanField(default=False)
    output_polygon_layer = serializers.CharField(required=False, allow_null=True)
    output_points_layer = serializers.CharField(required=False, allow_null=True)
    enable_point_labels = serializers.BooleanField(default=False)
    label_field = serializers.CharField(default="Bornes")
    label_color = serializers.CharField(default="#000000")
    label_size = serializers.IntegerField(default=10, min_value=1, max_value=100)
    label_offset_x = serializers.IntegerField(default=0)
    label_offset_y = serializers.IntegerField(default=0)

class RasterLayerAddSerializer(serializers.Serializer):
    data_source = serializers.CharField()
    layer_name = serializers.CharField(default="Couche Raster")
    session_id = serializers.UUIDField()

class MapRenderSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    width = serializers.IntegerField(default=800, min_value=100, max_value=4000)
    height = serializers.IntegerField(default=600, min_value=100, max_value=4000)
    dpi = serializers.IntegerField(default=96, min_value=72, max_value=600)
    format_image = serializers.ChoiceField(choices=['png', 'jpg', 'jpeg'], default='png')
    quality = serializers.IntegerField(default=90, min_value=1, max_value=100)
    background = serializers.CharField(default='transparent')
    bbox = serializers.CharField(required=False, allow_null=True)
    scale = serializers.FloatField(required=False, allow_null=True, min_value=0.1)
    show_points = serializers.JSONField(required=False, allow_null=True)
    points_style = serializers.ChoiceField(choices=['circle', 'square', 'triangle'], default='circle')
    points_color = serializers.CharField(default='#FF0000')
    points_size = serializers.IntegerField(default=10, min_value=1, max_value=50)
    points_labels = serializers.BooleanField(default=False)
    show_grid = serializers.BooleanField(default=False)
    grid_type = serializers.ChoiceField(choices=['lines', 'dots', 'crosses'], default='lines')
    grid_spacing = serializers.FloatField(default=1.0, min_value=0.001)
    grid_color = serializers.CharField(default='#0000FF')
    grid_width = serializers.IntegerField(default=1, min_value=1, max_value=10)
    grid_size = serializers.IntegerField(default=3, min_value=1, max_value=20)
    grid_labels = serializers.BooleanField(default=False)
    grid_label_position = serializers.ChoiceField(
        choices=['corners', 'edges', 'all'], default='edges'
    )
    grid_vertical_labels = serializers.BooleanField(default=False)
    grid_label_font_size = serializers.IntegerField(default=8, min_value=6, max_value=20)

class PDFGenerateSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    layout_config = serializers.JSONField(default=dict)
    output_filename = serializers.CharField(default='generated_report.pdf')

class QRScanSerializer(serializers.Serializer):
    qr_data = serializers.CharField()