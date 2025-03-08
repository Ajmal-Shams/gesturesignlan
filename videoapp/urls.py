from django.urls import path
from .views import home,detection,gesture,learn_asl,speechtotext,quiz,quick_phrases,custom_phrases, delete_phrase, search_phrases

urlpatterns = [
    path('', home, name='home'),
    path('detection/', detection, name='detection'),
    path('gesture/', gesture, name='gesture'),
    path('learn_asl/', learn_asl, name='learn_asl'),
    path('speechtotext/', speechtotext, name='speechtotext'),
    path('quiz/', quiz, name='quiz'),
    path('quick-phrases/', quick_phrases, name='quick_phrases'),
    path("custom-phrases/", custom_phrases, name="custom_phrases"),
    path("delete-phrase/<int:phrase_id>/", delete_phrase, name="delete_phrase"),
    path("search-phrases/", search_phrases, name="search_phrases"),


]
