# CareConnect

CareConnect is a semester 8 project, designed to act as a sympathetic medical chatbot. Patients can interact with the chatbot to communicate their medical issues. The chatbot will generate a detailed report and recommend a suitable doctor for the patient. The report will be forwarded to the designated doctor, along with the patient's contact details and available time slots for a consultation. The patient's medical history will be securely stored and managed.

---

## **Installation:**

### To run CareConnect, follow these steps:

1. Clone this repository to your local machine.
2. Navigate to the MainProject directory.
3. Create a virtual environment: ```python3 -m venv venv```
4. Activate the venv: 
    - For mac/linux:
        ```. venv/bin/activate```
    - For Windows:
        ```. venv/Scripts/activate```
5. Install the required dependencies by running the command `pip install -r requirements.txt`.
6. Initialise the env file:
    - Run ```cp dotenv .env```
    - Copy the credentials from the Auth0 application and fill it in the placeholders
7. Create migrations using the command `python manage.py makemigrations`
8. Migrate all the migrations to the model using the command `python manage.py migrate`
9. Start the Django development server using the command `python manage.py runserver`.
19. Access the application at [http://127.0.0.1:8000](http://127.0.0.1:8000).

### Returning users:

1. Activate the venv
2. Make migrations
3. Migrate the changes
4. Run the server

### Exit the app:

1. Use keyboard interrupt to exit the Django server: 
    - ```ctrl + C```
2. Deactivate the venv:
    - ```deactivate```


# **Contributing:**

If you'd like to contribute to CareConnect, please follow these steps:

1. Fork the repository on GitHub.
2. Create a new branch with a descriptive name.
3. Make your changes and commit them with clear, concise messages.
4. Push the changes to your fork.
5. Create a pull request, explaining the changes made.

---

# **License:**

This project is licensed under the [MIT License](LICENSE).

---

# **Contact:**

For further information or inquiries, please contact:

- [CareConnect](mailto:careconnect.ajce@gmail.com)

---