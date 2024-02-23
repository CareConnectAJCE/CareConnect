<div style="background-color: white;">
    <p align="center">
      <a rel="noopener noreferrer" target="_blank" href="https://careconnect.dev">
        <img src="/home/static/home/img/logo.png" />
      </a>
    </p>
</div>

CareConnect is a sympathetic medical chatbot designed to assist patients in communicating their medical issues. The chatbot generates a detailed report and recommends a suitable doctor for the patient. The report is forwarded to the designated doctor along with the patient's contact details and available time slots for consultation. Patient medical history is securely stored and managed.

---

## Installation and Development

### Running CareConnect:

1. Clone this repository to your local machine.
2. Navigate to the MainProject directory.
3. Create a virtual environment:
    - Mac/Linux:
      ```bash
      python3 -m venv venv
      ```
    - Windows:
      ```bash
      python -m venv venv
      ```
4. Activate the virtual environment:
    - Mac/Linux:
      ```bash
      source venv/bin/activate
      ```
    - Windows:
      ```bash
      source venv\Scripts\activate
      ```
5. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Initialize the environment file:
   ```bash
   cp dotenv .env
   ```
   - Fill in the credentials from the Auth0 application and also add the OpenAI API Key.
7. Checkout the `localdev` branch (`additional-features` for testing eye disease).
8. Create migrations:
   ```bash
   python manage.py makemigrations
   ```
9. Migrate the changes:
   ```bash
   python manage.py migrate
   ```
10. Start the Django development server:
    ```bash
    python manage.py runserver
    ```
11. Access the application at [http://127.0.0.1:8000](http://127.0.0.1:8000).

### Returning Users:

1. Activate the virtual environment.
2. Change the branch.
3. Make migrations.
4. Migrate the changes.
5. Run the server.

### Exiting the App:

1. Use `ctrl + C` to exit the Django server.
2. Deactivate the virtual environment:
    - ```bash
      deactivate
      ```

## Contributing:

To contribute to CareConnect, follow these steps:

1. Fork the repository on GitHub.
2. Create a new branch from `localdev` with a descriptive name.
3. Make changes and commit them with clear, concise messages.
4. Push changes to your fork.
5. Create a pull request, explaining the changes made to the `localdev` branch.

---

## License:

This project is licensed under the [MIT License](LICENSE).

---

## Contact:

For further information or inquiries, please contact:

- [CareConnect](mailto:careconnect.ajce@gmail.com)