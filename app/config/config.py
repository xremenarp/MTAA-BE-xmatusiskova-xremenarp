from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from OpenSSL import crypto

load_dotenv()

class Settings(BaseSettings):
    class Config:
        case_sensitive = True

    NAME: str
    DATABASE_HOST: str
    DATABASE_PORT: str
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    JWT_SECRET_KEY: str
    ALGORITHM: str


settings = Settings()

##chatgpt
def generate_ssl_cert_and_key(key_length=2048, days_valid=365):
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
#from hypercorn.config import Config
#config = Config()
##config.bind = ["0.0.0.0:443"]
#config.bind = ["192.168.0.63:8000"] ##bez https
##config.bind = ["127.0.0.2:443"] ##zo https
##config.certfile = "cert.pem"
##config.keyfile = "key.pem"
