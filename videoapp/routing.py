from django.urls import re_path
from .consumers import VideoProcessorConsumer ,GestureRecognitionConsumer

websocket_urlpatterns = [
    re_path(r'ws/video/$', VideoProcessorConsumer.as_asgi()),
    re_path(r'ws/gesture/$', GestureRecognitionConsumer.as_asgi()),

]
