# Required imports
from typing import Literal
from operator import itemgetter
import math

# Langchain imports
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnableBranch, RunnablePassthrough, RunnableLambda
from langchain.output_parsers.openai_functions import PydanticAttrOutputFunctionsParser
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.globals import set_verbose

# Models import
from .models import Report, Doctor, Conversation

set_verbose(True)

class ScheduleAppointment:
    """
    Represents a final chat between a user and a doctor.

    Attributes:
        user (User): The user participating in the chat.
        random_no (int): A random number used for session identification.
        message (String): A message from the final chat

    Methods:
        schedule_appointment(message): Schedule an appointment based on the user's message.
        save_report(response): Save the report of the user.
    """
    def __init__(self, user, message, random_no):
        self.user = user
        self.message = message
        self.random_no = random_no
        self.memory = ConversationBufferMemory(return_messages=True)
        self.memory.load_memory_variables({})

        _input_conversation = Conversation.objects.filter(user=self.user, session_id=self.random_no, is_user_message=True).order_by('id')
        _output_conversation = Conversation.objects.filter(user=self.user, session_id=self.random_no, is_user_message=False).order_by('id')

        self.message_query = ""

        for i in range(len(_input_conversation)):
            self.memory.save_context({"input": _input_conversation[i].message_content}, {"output": _output_conversation[i].message_content})
            self.message_query += "User: " + _input_conversation[i].message_content + "\n" + "Doctor: " + _output_conversation[i].message_content + "\n"

    def save_report(self, response):
        report = Report.objects.create(
            user=self.user,
            symptoms=",".join(response["symptoms"]) if len(response["symptoms"]) > 0 else "",
            predicted_disease=response["predicted_disease"]
        )
        report.save()

    def schedule_appointment(self, message):
        """
        Schedule an appointment based on the user's message.

        Args:
            message (str): The user's message.

        Returns:
            str: A message indicating that the appointment scheduling process has started.
        """
        model = ChatOpenAI(temperature=0.6)

        class Schedule(BaseModel):
            symptoms: list[str] = Field(
                description="The list of symptoms the patient has based on the chat history"
            )
            predicted_disease: str = Field(
                description="The disease predicted from the symptoms"
            )

        parser = JsonOutputParser(pydantic_object=Schedule)

        prompt = PromptTemplate(
            template="Answer the user query.\n{format_instructions}\n{query}\n",
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        chain = (
            RunnablePassthrough.assign(
                history=RunnableLambda(self.memory.load_memory_variables)
                | itemgetter("history")
            )
            | prompt
            | model
            | parser
        )

        response = chain.invoke({"query": self.message_query + "\nUser: " + message})

        report = Report.objects.create(
            user=self.user,
            symptoms=(
                ",".join(response["symptoms"]) if len(response["symptoms"]) > 0 else ""
            ),
            predicted_disease=response["predicted_disease"],
        )

        report.save()
        return "Starting your appointment scheduling process. Please wait for a moment."

class Chat:
    """
    Represents a chat between a user and a doctor.

    Args:
        user (User): The user participating in the chat.
        random_no (int): A random number used for session identification.

    Attributes:
        user (User): The user participating in the chat.
        memory (ConversationBufferMemory): The memory buffer for storing conversation history.
        random_no (int): A random number used for session identification.

    Methods:
        get_bot_response(user_message): Generates a response from the bot based on the user's message.
        schedule_appointment(message): Schedule an appointment based on the user's message.
        get_possible_symptoms(symptoms): Get possible symptoms based on the given symptoms.
        suitable_doctor_symptom(symptoms, latitude, longitude): Find a suitable doctor based on symptoms, latitude, and longitude.
    """
    def __init__(self, user, random_no):
            """
            Initializes an instance of the class.

            Args:
                user: An object representing the user.
                random_no: A random number.

            Returns:
                None
            """
            self.user = user
            self.memory = ConversationBufferMemory(return_messages=True)
            self.random_no = random_no
            self.memory.load_memory_variables({})

            main_prompt = f"""
            The following is a conversation with a doctor. The doctor is helping the patient with their health issues. \
            The patient is {self.user.first_name} {self.user.last_name}. \
            Try to use patients name in initial conversation. \
            The doctor is a very helpful, loyal and friendly person. \
            The doctor keeps track of the symptoms of the patient. \
            The doctor makes sure that the patient is calm and the doctor won't tell \
            the patient directly about the seriousness of the disease or what the disease is. \
            The doctor would suggest the patient with some home remedies if its a minor disease \
            or ask if the patient wants an appointment scheduled in our hospital and if yes \
            respond with 'I will schedule now!' only. \
            Don't ask any other details if the patient wants to schedule an appointment but \
            only respond with 'I will schedule now!' and stop the conversation. \
            If its a major disease like cancer or tuberculosis, tell the patient that \
            'I will schedule now!' and end the conversation with that. Don't ask any other details. \
            """

            general_prompt = f"""
            Don't answer any questions that are not related to health. \
            The patient is {self.user.first_name} {self.user.last_name}. \
            The patient is having a conversation with a doctor. \
            The doctor is a very helpful, loyal and friendly person. \
            The doctor is very good at his job. \
            No matter what the patient asks, if its not related to health, \
            the doctor should not answer the question. Instead, the doctor should ask the patient \
            if he/she has any health related questions. \
            If the patient wants an appointment scheduled in our hospital and if yes \
            respond with 'I will schedule now!' only. \
            Reply with 'Bye!' if the patient is ending the chat. 
            """

            schedule_prompt = f"""
            You are an appointment scheduler that helps people to schedule appointments. \
            Reply only with 'I will schedule now!' if the patient wants to schedule an appointment \
            and if the patient says yes to schedule after you ask that to patient. \
            Don't ask any other questions if the patient wants to schedule an appointment, just say \
            'I will schedule now!' nothing more and nothing less. 
            """

            general_prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", general_prompt),
                    MessagesPlaceholder(variable_name="history"),
                    ("human", "{input}"),
                ]
            )

            doctor_prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", main_prompt),
                    MessagesPlaceholder(variable_name="history"),
                    ("human", "{input}"),
                ]
            )

            schedule_prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", schedule_prompt),
                    MessagesPlaceholder(variable_name="history"),
                    ("human", "{input}"),
                ]
            )

            prompt = RunnableBranch(
                (
                    lambda x: print("Topic:", x["topic"]) or x["topic"] == "patient query",
                    doctor_prompt_template,
                ),
                (
                    lambda x: print("Topic:", x["topic"])
                    or x["topic"] == "schedule appointment query",
                    schedule_prompt_template,
                ),
                general_prompt_template,
            )

            class TopicClassifier(BaseModel):
                "Classify the topic of the user question"
                topic: Literal["general", "patient query", "schedule appointment query"]
                "The topic of the user question. One of 'patient query' or 'general' or 'schedule query'."

            classifier_function = convert_to_openai_function(TopicClassifier)

            llm = ChatOpenAI().bind(
                functions=[classifier_function], function_call={"name": "TopicClassifier"}
            )
            parser = PydanticAttrOutputFunctionsParser(
                pydantic_schema=TopicClassifier, attr_name="topic"
            )
            classifier_chain = llm | parser

            self.final_chain = (
                RunnablePassthrough.assign(
                    history=RunnableLambda(self.memory.load_memory_variables)
                    | itemgetter("history")
                )
                | RunnablePassthrough.assign(topic=itemgetter("input") | classifier_chain)
                | prompt
                | ChatOpenAI()
                | StrOutputParser()
            )

    def get_bot_response(self, user_message):
            """
            Generates a response from the bot based on the user's message.

            Args:
                user_message (str): The message inputted by the user.

            Returns:
                str: The response generated by the bot.
            """
            context = {"input": user_message}
            if "bye" in user_message.lower():
                response = "Bye! Have a nice day😇"
                self.memory.save_context(context, {"output": response})
            else:
                result = self.final_chain.invoke(context)

                self.memory.save_context(context, {"output": result})

                if "bye" in result.lower():
                    response = "Bye! Have a nice day😇"
                elif "i will schedule now!" in result.lower():
                    chat = ScheduleAppointment(self.user, user_message, self.random_no)
                    response = chat.schedule_appointment(
                        "What all symptoms do I have? And what is the predicted disease?"
                    )
                else:
                    response = result

            Conversation.objects.create(
                user=self.user,
                is_user_message=True,
                message_content=user_message,
                session_id=self.random_no,
            )
            Conversation.objects.create(
                user=self.user,
                is_user_message=False,
                message_content=response,
                session_id=self.random_no,
            )

            return response

    def get_possible_symptoms(self, symptoms):
            """
            Get possible symptoms based on the given symptoms.

            Args:
                symptoms (list[str]): The list of symptoms the patient has.

            Returns:
                list[str]: The list of other possible symptoms the patient might have.
            """
            model = ChatOpenAI(temperature=0.3)

            class Symptoms(BaseModel):
                symptoms: list[str] = Field(
                    description="The list of other symptoms the patient might have"
                )

            parser = JsonOutputParser(pydantic_object=Symptoms)

            prompt = PromptTemplate(
                template="Answer the user query by predicting other possible symptoms.\n{format_instructions}\n{query}\n",
                input_variables=["query"],
                partial_variables={"format_instructions": parser.get_format_instructions()},
            )

            chain = (
                RunnablePassthrough.assign(
                    history=RunnableLambda(self.memory.load_memory_variables)
                    | itemgetter("history")
                )
                | prompt
                | model
                | parser
            )

            response = chain.invoke({"query": ",".join(symptoms)})
            return response["symptoms"]

    def suitable_doctor_symptom(self, symptoms, latitude, longitude):
        """
        Find the suitable doctor for the patient based on their symptoms, latitude, and longitude.

        Args:
            symptoms (str): The symptoms of the patient.
            latitude (float): The latitude of the patient's location.
            longitude (float): The longitude of the patient's location.

        Returns:
            dict: A dictionary containing the ID of the suitable doctor and the predicted disease.

        """
        doctors = Doctor.objects.all()

        doctor_details = ""
        for doctor in doctors:

            distance = 6371 * (
                math.acos(
                    math.sin(math.radians(latitude))
                    * math.sin(math.radians(doctor.latitude))
                    + math.cos(math.radians(latitude))
                    * math.cos(math.radians(doctor.latitude))
                    * math.cos(math.radians(doctor.longitude) - math.radians(longitude))
                )
            )
            if distance <= 10:
                doctor_details += f"ID: {doctor.user.id} -> {doctor.user.first_name} {doctor.user.last_name} - {doctor.specialization}\n"

        # Use OpenAI and the predicted disease to find the suitable doctor
        doctor_details_prompt = f"""
        You are the receptionist of the hospital. \
        You have to find the suitable doctor for the patient. \
        These are the list of doctors who can help you with your symptoms. \
        {doctor_details} \
        The patient has the following symptoms: {symptoms} \
        Find the suitable doctor for the patient. \
        Reply with the ID of the doctor who can help the patient and \
        the predicted disease based on the symptoms.
        """

        model = ChatOpenAI(temperature=0.3)

        class DoctorDetails(BaseModel):
            doctor_id: str = Field(
                description="The ID of the doctor who can help the patient"
            )
            predicted_disease: str = Field(
                description="The disease the doctor thinks the patient has"
            )

        parser = JsonOutputParser(pydantic_object=DoctorDetails)

        prompt = PromptTemplate(
            template="Answer the user query.\n{format_instructions}\n{query}\n",
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        chain = (
            RunnablePassthrough.assign(
                history=RunnableLambda(self.memory.load_memory_variables)
                | itemgetter("history")
            )
            | prompt
            | model
            | parser
        )

        response = chain.invoke({"query": doctor_details_prompt})
        return {
            "doctor_id": response["doctor_id"],
            "predicted_disease": response["predicted_disease"],
        }