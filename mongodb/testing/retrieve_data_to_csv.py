import csv

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import ConnectionFailure

try:
    client = MongoClient("mongodb://dan:test@0.0.0.0:27017", server_api=ServerApi('1'))
    client.admin.command('ping')
except ConnectionFailure as e:
    print(f"Could not connect to mongoDB database {e}")

timestamp_start = 1754590360

plant_db = client["plant_data"]
plant_collection = plant_db["plant_1"]

documents_query = plant_collection.find({"timestamp": {"$gt": timestamp_start}})

fieldnames = ['_id', 'timestamp', 'temperature', 'relative_humidity', 'lux', 'moisture_value', 'moisture_percent']

with open('output.csv', 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for doc in documents_query:
        if '_id' in doc:
            doc['_id'] = str(doc['_id'])
        writer.writerow(doc)
        print(doc)

client.close()