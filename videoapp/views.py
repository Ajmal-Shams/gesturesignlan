from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import CustomPhrase

def home(request):
    return render(request, "home.html")

def detection(request):
    return render(request, "detection.html")

def gesture(request):
    return render(request, "gesture.html")

def learn_asl(request):
    return render(request, "learn_asl.html")

def speechtotext(request):
    return render(request, "speechtotext.html")

def quiz(request):
    return render(request, "quiz.html")

def quick_phrases(request):
    return render(request, 'quick_phrases.html')



def custom_phrases(request):
    if request.method == "POST":
        phrase_text = request.POST.get("phrase")
        if phrase_text:
            CustomPhrase.objects.create(text=phrase_text)
        return redirect("custom_phrases")

    phrases = CustomPhrase.objects.all()
    return render(request, "custom_phrases.html", {"phrases": phrases})

def delete_phrase(request, phrase_id):
    phrase = CustomPhrase.objects.get(id=phrase_id)
    phrase.delete()
    return redirect("custom_phrases")

def search_phrases(request):
    query = request.GET.get("q", "")
    results = CustomPhrase.objects.filter(text__icontains=query)
    return JsonResponse({"results": [p.text for p in results]})
