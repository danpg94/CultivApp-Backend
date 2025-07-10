from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Connection test using a container with the following command:
# docker run -d --name mongo-test -e MONGO_INITDB_ROOT_USERNAME=dan -e MONGO_INITDB_ROOT_PASSWORD=test \
# -p 27017:27017 -v mongotest:/data/db mongodb-raspberrypi4-unofficial-r7.0.14:late

client = MongoClient("mongodb://dan:test@0.0.0.0:27017", server_api=ServerApi('1'))
client.admin.command('ping')
print(client.list_database_names())