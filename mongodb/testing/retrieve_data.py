from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import ConnectionFailure

try:
    client = MongoClient("mongodb://dan:test@0.0.0.0:27017", server_api=ServerApi('1'))
    client.admin.command('ping')
except ConnectionFailure as e:
    print(f"Could not connect to mongoDB database {e}")

plant_db = client["plant_data"]
plant_collection = plant_db["plant_1"]

all_documents_cursor = plant_collection.find({})

print("All documents in the collection:")
for document in all_documents_cursor:
    print(document)

client.close()