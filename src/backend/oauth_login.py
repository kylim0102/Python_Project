
import google.oauth2.credentials
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
import json

import os

CLIENT_SECRETS_PATH = 'D:/K-Digital Training/Saturday/TeamProject/src/backend/client_secret.json'
print(os.path.exists(CLIENT_SECRETS_PATH))

class OAuthFlow:
    def __init__(self):

        with open(CLIENT_SECRETS_PATH, 'r') as file:
            data = json.load(file)
            client_id = data['installed']['client_id']
            client_secret = data['installed']['client_secret'] 

        # self.flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_PATH,
            scopes=['openid', 
                    'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile',
                    'https://www.googleapis.com/auth/calendar'
                    ],
            state='12345678910',
        )
        # self.flow.redirect_uri = "http://localhost:8080/login/oauth2/code/google"  # 리디렉션 URI

        flow.client_id = client_id  # client_id를 명시적으로 설정
        flow.client_secret = client_secret  # client_secret을 명시적으로 설정
        flow.redirect_uri = 'http://127.0.0.1:8000/oauth2callback'

    def get_authorization_url(self):
        authorization_url, state = self.flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return authorization_url   

    def fetch_credentials(self, authorization_response):
        self.flow.fetch_token(authorization_response=authorization_response)
        return self.flow.credentials

    def verify_id_token(self, credentials):
        # id_token 검증
        idinfo = id_token.verify_oauth2_token(credentials.id_token, 
                                              requests.Request(), 
                                              credentials.client_id)
        return idinfo

# def verify_id_token_form_uri(uri):
#     flow.fetch_token(authorization_response=uri)
#     return verify_id_token(flow.credentials)

 



