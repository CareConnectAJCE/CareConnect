# Required imports
import json
from urllib.parse import quote_plus, urlencode

# Utils and Models import
from .models import Conversation, Appointment
from .forms import UserEditForm

# OpenAI imports
from openai import OpenAI

# Langchain imports
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chat_models import ChatVertexAI, ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableBranch, RunnablePassthrough, RunnableLambda
from langchain.output_parsers.openai_functions import PydanticAttrOutputFunctionsParser
from langchain.utils.openai_functions import convert_pydantic_to_openai_function
from langchain_core.pydantic_v1 import BaseModel

# Auth0 imports
from authlib.integrations.django_client import OAuth

# Django imports
from django.shortcuts import get_object_or_404, render, redirect, reverse
from django.db.models import Q
from django.conf import settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

User = get_user_model()

oauth = OAuth()
oauth.register(
    "auth0",
    client_id=settings.AUTH0_CLIENT_ID,
    client_secret=settings.AUTH0_CLIENT_SECRET,
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f"https://{settings.AUTH0_DOMAIN}/.well-known/openid-configuration",
)

client = OpenAI()
messages = []

current_time = timezone.now()

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
        user.save()

    request.session["user"] = token
    request.user = user
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
    print(request.session)
    if request.session.get("user"):
        user = User.objects.get(sub=request.session["user"]["userinfo"]["sub"])
    else:
        user = None
    return render(
        request,
        "home/index.html",
        context={
            "session": request.session.get("user"),
            "user": user,
            "pretty": json.dumps(request.session.get("user"), indent=4),
        },
    )

def contact(request):
    return render(request, "home/contact.html")

def about(request):
    return render(request, "home/about.html")

def edit_user(request):
    if request.method == 'POST':
        try:
            username = request.POST['username']
            email = request.POST['email']
            first_name = request.POST['first_name']
            last_name = request.POST['last_name']

            user = User.objects.get(sub=request.session["user"]["userinfo"]["sub"])
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            return JsonResponse({'success': True})  # Return a JSON response

        except Exception as e:
            # Handle exceptions (e.g., if the user doesn't exist)
            print(e)
            return JsonResponse({'success': False, 'error_message': str(e)})

    # Handle other HTTP methods if needed
    return JsonResponse({'success': False, 'error_message': 'Invalid HTTP method'})


def doctor_view(request):
    user = User.objects.get(sub=request.session["user"]["userinfo"]["sub"])
    appointments = Appointment.objects.filter(doctor=user)
    history = Appointment.objects.filter(
        Q(user=user, appointment_time__lt=current_time, visited=True) | Q(user=user, visited=True)
    )
    return render(
        request,
        "home/doctor.html",
        context={
            "appointments": appointments,
            "history": history,
            "session": request.session.get("user"),
            "user": user,
            "pretty": json.dumps(request.session.get("user"), indent=4),
        },
    )

def patient_view(request):
    user = User.objects.get(sub=request.session["user"]["userinfo"]["sub"])
    appointments = Appointment.objects.filter(user=user, appointment_time__gte=current_time, visited=False)
    history = Appointment.objects.filter(
        Q(user=user, appointment_time__lt=current_time, visited=True) | Q(user=user, visited=True)
    )
    return render(
        request,
        "home/patient.html",
        context={
            "appointments": appointments,
            "history": history,
            "session": request.session.get("user"),
            "user": user,
            "pretty": json.dumps(request.session.get("user"), indent=4),
        },
    )

def appointment_visited(request):
    appointment_id = request.POST["appointment_id"]
    appointment = Appointment.objects.get(id=appointment_id)
    appointment.visited = True
    appointment.visited_time = timezone.now()
    appointment.save()
    return redirect(reverse("patient"))

def appointment_deleted(request):
    appointment_id = request.POST["appointment_id"]
    appointment = Appointment.objects.get(id=appointment_id)
    appointment.delete()
    return redirect(reverse("patient"))

# Landing pages views end

# Chatbot views and functions
def chatbot_landing(request):
    return render(request, "home/chatbot.html", context={
        "session": request.session.get("user"),
        "pretty": json.dumps(request.session.get("user"), indent=4),
    })

def get_completion(request, prompt, model="gpt-3.5-turbo"):
    user = User.objects.filter(sub=request.session["user"]["userinfo"]["sub"])
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