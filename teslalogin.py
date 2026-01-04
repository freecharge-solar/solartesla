from main import TeslaAuth
from config import TESLA_CLIENT_ID, TESLA_CLIENT_SECRET


if __name__ == "__main__":
    tesla_auth = TeslaAuth(TESLA_CLIENT_ID, TESLA_CLIENT_SECRET)
    tesla_auth.login()