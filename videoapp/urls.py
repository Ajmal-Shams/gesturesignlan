from django.urls import path
from .views import home,detection,gesture

urlpatterns = [
    path('', home, name='home'),
    path('detection/', detection, name='detection'),
    path('gesture/', gesture, name='gesture'),

]
