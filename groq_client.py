import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

groq_api_key=os.getenv("GROQ_API_KEY")

client = Groq(api_key=groq_api_key)