import requests
import base64

# Testing with a GET request
response = requests.get('http://localhost:8000/upload')



# Combine username and password
credentials = "500:204" #NTAwOjIwNA==

# Encode in Base64
encoded_credentials = base64.b64encode(credentials.encode()).decode()
print(encoded_credentials)

