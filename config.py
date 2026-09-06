from dotenv import load_dotenv
import os
load_dotenv()
DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
class Config:
    SQLALCHEMY_DATABASE_URI = DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False


