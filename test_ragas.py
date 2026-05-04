import os
from dotenv import load_dotenv
load_dotenv()

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

llm = ChatGroq(model='llama-3.3-70b-versatile', temperature=0)
embeddings = HuggingFaceEmbeddings(model_name='BAAI/bge-m3')

data = {
    'question': ['¿Qué es el contrabando?'],
    'answer': ['El contrabando es introducir mercancías sin control aduanero según Art. 1 Ley 28008'],
    'contexts': [['El contrabando según la Ley 28008 es la introducción de mercancías sin control aduanero']],
    'ground_truth': ['El contrabando es un delito aduanero según la Ley 28008'],
}
dataset = Dataset.from_dict(data)
result = evaluate(dataset, metrics=[faithfulness, answer_relevancy], llm=llm, embeddings=embeddings)
print('Faithfulness:', result['faithfulness'])
print('Answer Relevancy:', result['answer_relevancy'])
