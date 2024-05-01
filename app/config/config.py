"""
Configuration of environment (using dotenv) variables and
SSL certificate generation for a server application HTTPS for
secure communication.
"""

from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from OpenSSL import crypto

load_dotenv()

class Settings(BaseSettings):
    """
    Configuration settings for the server application.

    Attributes:
        NAME: Name of the server application.
        DATABASE_HOST: Hostname of the database server.
        DATABASE_PORT: Port of the database server.
        DATABASE_NAME_CLIENT: Name of the client database.
        DATABASE_NAME_SERVER: Name of the server database.
        DATABASE_USER: Username for database access.
        DATABASE_PASSWORD: Password for database access.
        JWT_SECRET_KEY: Secret key for JWT token generation.
        ALGORITHM: Algorithm used for JWT token encryption.
    """
    class Config:
        """
        Configuration options for the settings class.
        """
        case_sensitive = True

    NAME: str
    DATABASE_HOST: str
    DATABASE_PORT: str
    DATABASE_NAME_CLIENT: str
    DATABASE_NAME_SERVER: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    JWT_SECRET_KEY: str
    ALGORITHM: str


settings = Settings()

##chatgpt
def generate_ssl_cert_and_key(key_length=2048, days_valid=365):
    """
    Function to generate SSL certificate and private key.

    Args:
        key_length:
            The length of the generated key, by default is 2048.
        days_valid:
            Number of days the certificate will be valid, by default it is one year.
    """
    # Generate a key pair
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, key_length)

    # Create a self-signed certificate
    cert = crypto.X509()
    cert.get_subject().C = "SK"  # Country Name
    cert.get_subject().ST = "BA"  # State or Province Name
    cert.get_subject().L = "BA"  # Locality Name
    cert.get_subject().O = "MTAA"  # Organization Name
    cert.get_subject().CN = "localhost"  # Common Name
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(days_valid * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')

    # Write certificate and private key to files
    with open('cert.pem', "wb") as certfile:
        certfile.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

    with open('key.pem', "wb") as keyfile:
        keyfile.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
    print("SSL certificate and key generated successfully.")

#generate_ssl_cert_and_key()
########from hypercorn.config import Config
#######config = Config()
##config.bind = ["0.0.0.0:443"]
######config.bind = ["192.168.0.63:8000"] ##bez https
#config.bind = ["192.168.0.63:443"] ##so https
#config.certfile = "cert.pem"
#config.keyfile = "key.pem"
