from django.urls import path
from .views import upload_file,speech_page

urlpatterns = [
    path("upload/", upload_file, name="upload_file"),
    path("speech/", speech_page, name="speech"),
]
