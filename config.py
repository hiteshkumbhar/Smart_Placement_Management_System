from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
class Config:
    SQLALCHEMY_DATABASE_URI = DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")                                  #Signs and verifies JWTs.
    JWT_TOKEN_LOCATION = ["headers", "cookies"]                                              #Tells Flask-JWT-Extended to read tokens from cookies.
    JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "False").lower() == "true" #Restricts cookies to HTTPS when enabled.
    JWT_COOKIE_HTTPONLY = True                                                    #Prevents JavaScript from directly reading the authentication cookie.
    JWT_COOKIE_SAMESITE = "Lax"                                                   #Helps restrict cross-site cookie sending.
    JWT_COOKIE_CSRF_PROTECT = True                                                #Enables CSRF protection for cookie-based JWT authentication.
    JWT_ACCESS_TOKEN_EXPIRES = 30 * 60                                            #Sets the access token lifetime to 30 minutes.
    JWT_REFRESH_TOKEN_EXPIRES = 7 * 24 * 60 * 60
    JWT_CSRF_CHECK_FORM = True

