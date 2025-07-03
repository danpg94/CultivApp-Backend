from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv, find_dotenv
import os
load_dotenv(find_dotenv())

password = os.environ.get("MONGODB_PWD")

uri = f"mongodb+srv://danpg94:<{password}>@cherry-cluster.n0x2vso.mongodb.net/?retryWrites=true&w=majority&appName=Cherry-Cluster"
client = MongoClient(uri)