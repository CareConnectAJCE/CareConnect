from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# Create your views here.
import os, shutil
import imghdr
from werkzeug.utils import secure_filename
from .generate_prediction import Predictions

ALLOWED_EXTENSIONS = ['.jpg', '.png', '.jpeg']
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'detection', 'static', 'detection', 'uploads')

def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image(stream):
    header = stream.read(512)  # 512 bytes should be enough for a header check
    stream.seek(0)  # reset stream pointer
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')

def eye_landing(request):
    if request.method == 'POST':
        print("Files: ", request.FILES)
        folder = UPLOAD_FOLDER
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

        uploaded_file = request.FILES['file']
        filename = secure_filename(uploaded_file.name)
        if filename != '':
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in ALLOWED_EXTENSIONS:
                return redirect(reverse('eye_landing'))
            default_storage.save(UPLOAD_FOLDER+f'/{filename}', ContentFile(uploaded_file.read()))

            x = Predictions()
            x.load_model()
            prediction = x.predict(UPLOAD_FOLDER + '/' + filename)
            print("Prediction: ", prediction)
            return render(request, 'detection/eye_index.html', context={
                "filename": filename, 
                "prediction": prediction, 
                "prediction_value": f"{100-prediction*100:.2f}"
            })
        
    folder = UPLOAD_FOLDER
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    return render(request, 'detection/eye_index.html')

def throat_landing(request):
    if request.method == 'POST':
        print("Files: ", request.FILES)
        folder = UPLOAD_FOLDER
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

        uploaded_file = request.FILES['file']
        filename = secure_filename(uploaded_file.name)
        if filename != '':
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in ALLOWED_EXTENSIONS:
                return redirect(reverse('detection:throat_landing'))
            default_storage.save(UPLOAD_FOLDER+f'/{filename}', ContentFile(uploaded_file.read()))

            x = Predictions()
            prediction = x.throat_predict(filename)

            return render(request, 'detection/throat_index.html', context={
                "filename": filename, 
                "prediction": prediction, 
            })
        
    folder = UPLOAD_FOLDER
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    return render(request, 'detection/throat_index.html')