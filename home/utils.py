from typing import Literal
from operator import itemgetter
import json
import math

# Langchain imports
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnableBranch, RunnablePassthrough, RunnableLambda
from langchain.output_parsers.openai_functions import PydanticAttrOutputFunctionsParser
from langchain.utils.openai_functions import convert_pydantic_to_openai_function
from langchain_core.pydantic_v1 import BaseModel, Field

# Models import
from .models import Report, Doctor

class FinalChat:
    def __init__(self, user, memory, message):
        self.user = user
        self.memory = memory
        self.message = message

    def save_report(self, response):
        report = Report.objects.create(
            user=self.user,
            symptoms=json.dumps(response.symptoms),
        )
        report.save()

    def schedule_appointment(self):
        model = ChatOpenAI(temperature=0.3)

        class Schedule(BaseModel):
            time: str = Field(description="Time the patient wants to schedule")
            symptoms: list[str] = Field(description="The list of symptoms the patient has")
            predicted_disease: str = Field(description="The disease the doctor thinks the patient has")

        parser = JsonOutputParser(pydantic_object=Schedule)

        prompt = PromptTemplate(
            template="Answer the user query.\n{format_instructions}\n{query}\n",
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        chain = (
            RunnablePassthrough.assign(
                history=RunnableLambda(self.memory.load_memory_variables) | itemgetter("history")
            )
            | prompt
            | model
            | parser
        )

        response = chain.invoke({"query": self.message})
        self.save_report(response)

class Chat:
    def __init__(self, user):
        self.user = user
        self.memory = ConversationBufferMemory(return_messages=True)
        self.memory.load_memory_variables({})
        print(self.user.first_name, self.user.last_name)
        main_prompt = f"""
        The following is a conversation with a doctor. The doctor is helping the patient with their health issues. \
        The patient is {self.user.first_name} {self.user.last_name}. \
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
        Reply with 'Bye!' if the patient is ending the chat. \
        Reply with 'Schedule' if the patient wants to schedule an appointment \
        and if the patient says yes to schedule.
        """

        general_prompt = f"""
        Don't answer any questions that are not related to health. \
        The patient is {self.user.first_name} {self.user.last_name}. \
        The patient is having a conversation with a doctor. \
        The doctor is a very helpful, loyal and friendly person. \
        The doctor is very good at his job. \
        No matter what the patient asks, if its not related to health, \
        the doctor should not answer the question. Instead, the doctor should ask the patient \
        to ask if the patient has any health related questions. \
        Reply with 'Bye!' if the patient is ending the chat. 
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

        prompt = RunnableBranch(
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

        self.final_chain = (
            RunnablePassthrough.assign(history=RunnableLambda(self.memory.load_memory_variables) | itemgetter("history"))
            | RunnablePassthrough.assign(topic=itemgetter("input") | classifier_chain)
            | prompt
            | ChatOpenAI()
            | StrOutputParser()
        )

    def get_bot_response(self, user_message):
        if "bye" in user_message.lower():
            return "Bye! Have a nice day😇"

        context = {"input": user_message}
        result = self.final_chain.invoke(context)

        self.memory.save_context(context, {"output": result})

        if "bye" in result.lower():
            return "Bye! Have a nice day😇"
        
        if "schedule" in result.lower():
            chat = FinalChat(self.user, self.memory, user_message)
            print(chat.schedule_appointment())
            return "Starting your appointment scheduling process. Please wait for a moment."
        
        return result
    
def get_possible_symptoms(symptoms):
    model = ChatOpenAI(temperature=0.3)

    class Symptoms(BaseModel):
        symptoms: list[str] = Field(description="The list of symptoms the patient has")

    parser = JsonOutputParser(pydantic_object=Symptoms)

    prompt = PromptTemplate(
        template="Answer the user query by predicting other possible symptoms.\n{format_instructions}\n{query}\n",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = (
        prompt
        | model
        | parser
    )

    response = chain.invoke({"query": symptoms})
    return response.symptoms

def suitable_doctor_symptom(symptoms, latitude, longitude):
    doctors = Doctor.objects.all()

    doctor_details = ""
    for doctor in doctors:
        # Use the equation =acos(sin(lat1)*sin(lat2)+cos(lat1)*cos(lat2)*cos(lon2-lon1))*6371 to find the distance between the patient and the doctor
        distance = 6371 * (math.acos(math.sin(math.radians(latitude)) * math.sin(math.radians(doctor.latitude)) + math.cos(math.radians(latitude)) * math.cos(math.radians(doctor.latitude)) * math.cos(math.radians(doctor.longitude) - math.radians(longitude))))
        if distance <= 10:
            doctor_details += f"ID: {doctor.user.sub} -> {doctor.user.first_name} {doctor.user.last_name} - {doctor.specialization}\n"

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
        doctor_id: str = Field(description="The ID of the doctor who can help the patient"),
        predicted_disease: str = Field(description="The disease the doctor thinks the patient has")

    parser = JsonOutputParser(pydantic_object=DoctorDetails)

    prompt = PromptTemplate(
        template="Answer the user query.\n{format_instructions}\n{query}\n",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = (
        prompt
        | model
        | parser
    )

    response = chain.invoke({"query": doctor_details_prompt})
    return {
        "doctor_id": response.doctor_id,
        "predicted_disease": response.predicted_disease
    }