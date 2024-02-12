# Required imports
import json
import random
from urllib.parse import quote_plus, urlencode
from datetime import date, timedelta

# Utils and Models import
from .models import Appointment, Doctor, Report
from .utils import Chat

# OpenAI imports
from openai import OpenAI

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
        'first_name': user_info.get('given_name', ''),
        'last_name': user_info.get('family_name', ''),
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
        if (user.is_superuser):
            return redirect(reverse("admin"))
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
        Q(doctor=user, appointment_time__lt=current_time, visited=True) | Q(doctor=user, visited=True)
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

def admin_view(request):
    user = User.objects.get(sub=request.session["user"]["userinfo"]["sub"])
    doctor_applications = Doctor.objects.filter(user__is_doctor=False)
    doctors = Doctor.objects.filter(user__is_doctor=True)
    total_doctors = len(doctors)
    total_patients = len(User.objects.filter(is_doctor=False))
    total_appointments = len(Appointment.objects.all())
    return render(
        request,
        "home/admin.html",
        context={
            "doctors": doctors,
            "doctor_applications": doctor_applications,
            "session": request.session.get("user"),
            "user": user,
            "pretty": json.dumps(request.session.get("user"), indent=4),
            "total_doctors": total_doctors,
            "total_patients": total_patients,
            "total_appointments": total_appointments
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

def save_user_location(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        user = User.objects.get(sub=request.session["user"]["userinfo"]["sub"])
        user.latitude = data["lat"]
        user.longitude = data["lng"]
        user.save()
        return JsonResponse({"success": True})

def doctor_registration(request):
    user = User.objects.get(sub=request.session["user"]["userinfo"]["sub"])
    doctor = Doctor.objects.filter(user=user)
    if request.method == "GET":
        return render(
            request,
            "home/doctorreg.html",
            context={
                "session": request.session.get("user"),
                "user": user,
                "pretty": json.dumps(request.session.get("user"), indent=4),
                "applied": True if doctor else False,
            },
        )
    else:       
        first_name, last_name = request.POST["name"].split(" ") if " " in request.POST["name"] else (request.POST["name"], "")
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        doctor = Doctor.objects.get_or_create(
            user=user,
            specialization=request.POST["specialization"],
            qualification=request.POST["qualification"],
            experience=request.POST["experience"],
            phone=request.POST["phone"],
            address=request.POST["address"],
            city=request.POST["city"],
            state=request.POST["state"],
            country=request.POST["country"],
            zip=request.POST["pincode"],
            latitude=request.POST["latitude"],
            longitude=request.POST["longitude"]
        )

        doctor[0].save()
        return redirect(reverse("doctor_register"))
    
def approve_doctor(request, sub):
    doctor = Doctor.objects.get(user__sub=sub)
    doctor.user.is_doctor = True
    doctor.user.save()
    return redirect(reverse("admin"))

def appointment_visited(request):
    appointment_id = request.POST["appointment_id"]
    remarks = request.POST["remarks"]
    appointment = Appointment.objects.get(id=appointment_id)
    appointment.visited = True
    appointment.visited_time = timezone.now()
    appointment.doctor_remarks = remarks
    appointment.save()
    return redirect(reverse("doctor"))

def appointment_deleted(request):
    appointment_id = request.POST["appointment_id"]
    appointment = Appointment.objects.get(id=appointment_id)
    appointment.delete()
    return redirect(reverse("patient"))

def appointment(request):
    if request.method == "POST":
        user = User.objects.get(sub=request.session["user"]["userinfo"]["sub"])
        doctor = User.objects.get(sub=request.POST["doctor"])
        appointment = Appointment.objects.create(
            user=user,
            doctor=doctor,
            scheduled_time=request.POST["scheduled_time"],
        )
        appointment.save()
        return redirect(reverse("patient"))
    else:
        report = Report.objects.filter(user__sub=request.session["user"]["userinfo"]["sub"]).last()
        symptoms = report.symptoms.split(",")
        possible_symptoms = chat.get_possible_symptoms(symptoms)
        return render(
            request,
            "home/appointment.html",
            context={
                "symptoms": symptoms,
                "possible_symptoms": possible_symptoms,
                "session": request.session.get("user"),
                "pretty": json.dumps(request.session.get("user"), indent=4),
            },
        )
    
def predict_doctor_symptom(request):
    symptoms = request.GET.get("symptoms")
    user = User.objects.get(sub=request.session["user"]["userinfo"]["sub"])

    # save symptoms to the last report
    report = Report.objects.filter(user=user).last()
    report.symptoms = symptoms

    response = chat.suitable_doctor_symptom(symptoms, user.latitude, user.longitude)
    report.predicted_disease = response["disease"]
    report.save()
    
    return JsonResponse({
        "doctor_id": response["doctor_id"],
        "available_times": [f"{date.today() + timedelta(days=i)}" for i in range(1, 8)]
    })

# Landing pages views end

# Chatbot views and functions
def chatbot_landing(request):
    global chat
    try:
        random_no = random.randint(10000, 99999)
        chat = Chat(User.objects.get(sub=request.session["user"]["userinfo"]["sub"]), random_no)
    except Exception as e:
        print(e)
        return redirect(reverse("index"))
    return render(request, "home/chatbot.html", context={
        "session": request.session.get("user"),
        "pretty": json.dumps(request.session.get("user"), indent=4),
    })

def get_bot_response(request):
    user_message = request.GET.get('msg')
    response = chat.get_bot_response(user_message)

    return JsonResponse({'message': response})