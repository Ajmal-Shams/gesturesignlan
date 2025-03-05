from django.urls import path
from .views import home,detection,gesture,learn_asl

urlpatterns = [
    path('', home, name='home'),
    path('detection/', detection, name='detection'),
    path('gesture/', gesture, name='gesture'),
    path('learn_asl/', learn_asl, name='learn_asl'),

]
