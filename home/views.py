import json
from openai import OpenAI
from django.shortcuts import render, redirect, reverse
from authlib.integrations.django_client import OAuth
from django.conf import settings
from django.shortcuts import redirect, render
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
            "pretty": json.dumps(request.session.get("user"), indent=4),
        },
    )

def contact(request):
    return render(request, "home/contact.html")

def about(request):
    return render(request, "home/about.html")

# Landing pages views end

# Chatbot views and functions
def chatbot_landing(request):
    return render(request, "home/chatbot.html", context={
            "session": request.session.get("user"),
            "pretty": json.dumps(request.session.get("user"), indent=4),
        })

def get_completion(prompt, model="gpt-3.5-turbo"):
    messages.append({
        "role": "user",
        "content": f"The prompt by user is inside square brackets. Answer if the question is related to medical only or if its any greetings. If its greeting, reply appropriately and let it know that you are a medical bot. Otherwise let the user know the same: [{prompt}]",
    })
    response = client.chat.completions.create(
        messages=messages,
        model=model,
    )
    messages.append({
        "role": response.choices[0].message.role,
        "content": response.choices[0].message.content
    })
    return response.choices[0].message

def get_bot_response(request):    
    userText = request.GET
    response = get_completion(userText['msg'])
    return JsonResponse({
        'message': response.content
    })