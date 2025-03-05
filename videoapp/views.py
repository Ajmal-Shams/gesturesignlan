from django.shortcuts import render

def home(request):
    return render(request, "home.html")

def detection(request):
    return render(request, "detection.html")

def gesture(request):
    return render(request, "gesture.html")

def learn_asl(request):
    return render(request, "learn_asl.html")
