import os
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv

def exchange():
    load_dotenv()
    client_id = os.getenv('FYERS_CLIENT_ID')
    secret_key = os.getenv('FYERS_SECRET_KEY')
    redirect_uri = os.getenv('FYERS_REDIRECT_URL')
    auth_code = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBfaWQiOiJEUFhLMDIxVzRFIiwidXVpZCI6ImI4ZmFjNmRjYjUyMTQwY2U4NTRiZGFiM2M2NTE3MjMyIiwiaXBBZGRyIjoiIiwibm9uY2UiOiIiLCJzY29wZSI6IiIsImRpc3BsYXlfbmFtZSI6IkZBSjU5NzA3Iiwib21zIjoiSzEiLCJoc21fa2V5IjoiMDNhNWU4NDg0YzdjYWZkODI2MWI2YTczYjEzYzUxN2MwM2Y2NmJkNTgzYzkzMTlmZTkyMWJjNDgiLCJpc0RkcGlFbmFibGVkIjoiTiIsImlzTXRmRW5hYmxlZCI6Ik4iLCJhdWQiOiJbXCJkOjFcIixcImQ6MlwiLFwieDowXCIsXCJ4OjFcIl0iLCJleHAiOjE3Nzg1OTc3OTUsImlhdCI6MTc3ODU2Nzc5NSwiaXNzIjoiYXBpLmxvZ2luLmZ5ZXJzLmluIiwibmJmIjoxNzc4NTY3Nzk1LCJzdWIiOiJhdXRoX2NvZGUifQ._ZX_i6Nox3c9nLX-llUdwRiEhD25xPEkaV7AFWCv5jw'
    
    session = fyersModel.SessionModel(
        client_id=client_id, secret_key=secret_key,
        redirect_uri=redirect_uri, response_type='code', grant_type='authorization_code'
    )
    session.set_token(auth_code)
    response = session.generate_token()
    
    if 'access_token' in response:
        print(f"SUCCESS|{response['access_token']}|{response.get('refresh_token', '')}")
    else:
        print(f"FAILED|{response}")

if __name__ == '__main__':
    exchange()
