import json
import datetime
from .models import Conversation, Appointment
from openai import OpenAI
from django.shortcuts import render, redirect, reverse
from authlib.integrations.django_client import OAuth
from django.conf import settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from urllib.parse import quote_plus, urlencode
from django.http import JsonResponse

User = get_user_model()

oauth = OAuth()

client = OpenAI()
messages = []

oauth.register(
    "auth0",
    client_id=settings.AUTH0_CLIENT_ID,
    client_secret=settings.AUTH0_CLIENT_SECRET,
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f"https://{settings.AUTH0_DOMAIN}/.well-known/openid-configuration",
)

# Auth0 Views
def login(request):
    return oauth.auth0.authorize_redirect(
        request, request.build_absolute_uri(reverse("callback"))
    )

def callback(request):
    token = oauth.auth0.authorize_access_token(request)
    user_info = token.get("userinfo", {})
    sub = user_info.get("sub")

    # Check if the user already exists in the database
    user, created = User.objects.get_or_create(sub=sub, defaults={
        'email': user_info.get('email', ''),
        'sub': sub,
    })

    if not created:
        user.email = user_info.get('email', '')
        user.sub = sub
        user.last_login = user_info.get('updated_at', '')
        user.username = user_info.get('nickname', '')
        user.save()
    else:
        user.last_login = user_info.get('updated_at', '')

    request.session["user"] = token
    return redirect(reverse("index"))

def logout(request):
    request.session.clear()
    if len(messages)>=1:
        messages.clear()

    return redirect(
        f"https://{settings.AUTH0_DOMAIN}/v2/logout?"
        + urlencode(
            {
                "returnTo": request.build_absolute_uri(reverse("index")),
                "client_id": settings.AUTH0_CLIENT_ID,
            },
            quote_via=quote_plus,
        ),
    )

# Auth0 View End

# Index and landing pages

def index(request):
    return render(
        request,
        "home/index.html",
        context={
            "session": request.session.get("user"),
            "user": request.user,
            "pretty": json.dumps(request.session.get("user"), indent=4),
        },
    )

def contact(request):
    return render(request, "home/contact.html")

def about(request):
    return render(request, "home/about.html")

def doctor_view(request):
    userinfo = request.session["user"]["userinfo"]
    user = User.objects.get(username=userinfo["nickname"])
    appointments = Appointment.objects.filter(doctor=user)
    return render(
        request,
        "home/doctor.html",
        context={
            "appointments": appointments,
            "session": request.session.get("user"),
            "user": request.user,
            "pretty": json.dumps(request.session.get("user"), indent=4),
        },
    )

def patient_view(request):
    userinfo = request.session["user"]["userinfo"]
    user = User.objects.get(username=userinfo["nickname"])
    # appointments need to fetched that are todays data or after and history with date before today
    appointments = Appointment.objects.filter(user=user, appointment_time__gte=datetime.now())
    history = Appointment.objects.filter(user=user, appointment_time__lt=datetime.now())
    return render(
        request,
        "home/patient.html",
        context={
            "appointments": appointments,
            "history": history,
            "session": request.session.get("user"),
            "user": request.user,
            "pretty": json.dumps(request.session.get("user"), indent=4),
        },
    )

# Landing pages views end

# Chatbot views and functions
def chatbot_landing(request):
    return render(request, "home/chatbot.html", context={
        "session": request.session.get("user"),
        "pretty": json.dumps(request.session.get("user"), indent=4),
    })

def get_completion(request, prompt, model="gpt-3.5-turbo"):
    userinfo = request.session["user"]["userinfo"]
    user = User.objects.get(username=userinfo["nickname"])
    messages.append({
        "role": "user",
        "content": f"The prompt by user is inside square brackets. Answer if the question is related to medical only or if its any greetings. If its greeting, reply appropriately and let it know that you are a medical bot and also mention their name. If it is a medical prompt, ask and try to get more details about the same. Otherwise let the user know that you won't handle the issues: Prompt by {userinfo['name']}: [{prompt}]",
    })
    response = client.chat.completions.create(
        messages=messages,
        model=model,
    )
    messages.append({
        "role": response.choices[0].message.role,
        "content": response.choices[0].message.content
    })

    user_message = Conversation(user=user, is_user_message=True, message_content=prompt)
    user_message.save()

    bot_message = Conversation(user=user, is_user_message=False, message_content=response.choices[0].message.content)
    bot_message.save()

    return response.choices[0].message

def get_bot_response(request):    
    userText = request.GET
    response = get_completion(request, userText['msg'])
    return JsonResponse({
        'message': response.content
    })