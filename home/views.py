# Required imports
import json
from urllib.parse import quote_plus, urlencode
from typing import Literal
from operator import itemgetter

# Utils and Models import
from .models import Conversation, Appointment
from .forms import UserEditForm

# OpenAI imports
from openai import OpenAI

# Langchain imports
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableBranch, RunnablePassthrough, RunnableLambda
from langchain.output_parsers.openai_functions import PydanticAttrOutputFunctionsParser
from langchain.utils.openai_functions import convert_pydantic_to_openai_function
from langchain_core.pydantic_v1 import BaseModel

# Auth0 imports
from authlib.integrations.django_client import OAuth

# Django imports
from django.shortcuts import render, redirect, reverse
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

def initialize_chat(user):
    global final_chain, memory

    memory = ConversationBufferMemory(return_messages=True)
    memory.load_memory_variables({})

    main_prompt = f"""
    The following is a conversation with a doctor. The doctor is helping the patient with their health issues. \
    The patient is {user.first_name} {user.last_name}. \
    The doctor is a very helpful, loyal and friendly person. \
    The doctor is very good at his job. \
    The doctor keeps track of the symptoms of the patient. \
    The doctor makes sure that the patient is calm and won't tell the patient directly about \
    the seriousness of the disease or what the disease is. \
    The doctor would suggest the patient with some home remedies if its a minor disease. \
    The doctor would suggest the patient to go to the hospital if its a major disease \
    and asks if the patient needs to schedule a session with the doctor. \
    If the patient says yes, you should generate a json with the following format: \
    Time: Time the patient wants to schedule, Symptoms: The list of symptoms the patient has \
    and Predicted Disease: The disease the doctor thinks the patient has. \
    Try to use patients name in initial conversation. \
    """

    general_prompt = f"""
    Don't answer any questions that are not related to health. \
    The patient is {user.first_name} {user.last_name}. \
    The patient is having a conversation with a doctor. \
    The doctor is a very helpful, loyal and friendly person. \
    The doctor is very good at his job. \
    No matter what the patient asks, if its not related to health, \
    the doctor should not answer the question. Instead, the doctor should ask the patient \
    to ask if the patient has any health related questions. \
    """

    general_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", general_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    )

    doctor_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", main_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    )

    prompt_branch = RunnableBranch(
        (lambda x: x['topic'] == 'patient query', doctor_prompt),
        general_prompt
    )

    class TopicClassifier(BaseModel):
        "Classify the topic of the user question"
        topic: Literal['general', 'patient query']
        "The topic of the user question. One of 'patient query' or 'general'."

    classifier_function = convert_pydantic_to_openai_function(TopicClassifier)
    llm = ChatOpenAI().bind(
        functions=[classifier_function], function_call={"name": "TopicClassifier"}
    )
    parser = PydanticAttrOutputFunctionsParser(
        pydantic_schema=TopicClassifier, attr_name="topic"
    )
    classifier_chain = llm | parser

    final_chain = (
        RunnablePassthrough.assign(history=RunnableLambda(memory.load_memory_variables) | itemgetter("history"))
        | RunnablePassthrough.assign(topic=itemgetter("input") | classifier_chain)
        | prompt_branch
        | ChatOpenAI()
        | StrOutputParser()
    )

def chatbot_landing(request):
    initialize_chat(User.objects.get(sub=request.session["user"]["userinfo"]["sub"]))
    return render(request, "home/chatbot.html", context={
        "session": request.session.get("user"),
        "pretty": json.dumps(request.session.get("user"), indent=4),
    })

def get_bot_response(request):
    user_message = request.GET['msg']

    if "bye" in user_message.lower():
        return JsonResponse({
            'message': "Bye! Have a nice day😇"
        })

    context = {"input": user_message}
    result = final_chain.invoke(context)

    memory.save_context(context, {"output": result})
    
    return JsonResponse({
        'message': result
    })