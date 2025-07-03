from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv, find_dotenv
import os
load_dotenv(find_dotenv())

password = os.environ.get("MONGODB_PWD")

# URI for the cluster. Remember to have an .env file with password for MongoDB Atlas account
uri = f"mongodb+srv://danpg94:{password}@cherry-cluster.n0x2vso.mongodb.net/?retryWrites=true&w=majority&appName=Cherry-Cluster"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

dbs = client.list_database_names()
print(dbs)
test_db = client.test
collections = test_db.list_collection_names()
print(collections)

def insert_test_doc():
    collection = test_db.test
    test_document = {
        "name": "Daniel",
        "type": "Test",
    }
    inserted_id = collection.insert_one(test_document).inserted_id
    print(inserted_id)


def create_documents():
    production = client.production
    person_collection = production.person_collection
    first_names = ["Daniel", "Abraham", "Jose", "Ricardo", "Maximiliano"]
    last_names = ["Palma", "Gallardo", "Lopez", "Garcia", "Contreras"]
    ages = [31, 28, 45, 17, 23]

    docs = []

    for first_name, last_name, age in zip(first_names, last_names, ages):
        doc = {"first_name": first_name, "last_name": last_name, "age": age}
        docs.append(doc)
        # person_collection.insert_one(doc)

    person_collection.insert_many(docs)

create_documents()