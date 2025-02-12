from django.urls import re_path
from .consumers import VideoProcessorConsumer

websocket_urlpatterns = [
    re_path(r'ws/video/$', VideoProcessorConsumer.as_asgi()),
]
