import streamlit as st
import pandas as pd
import openai
import os
import io
from io import StringIO
import gspread
import requests
from google.cloud import storage
import json
import pymongo
from pymongo import MongoClient
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
load_dotenv()

#with open('apikey.txt','r') as file:
#    openai.api_key = file.read()
openai.api_key = os.environ.get('openai_key')


sheet_id=os.environ.get('sheet_id')
sheet_name= ['LEAD', 'RATIOS','COMPANY DATA', 'FINANCIAL DATA']#"leads"
url_csv=f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name[3]}"
# Function to fetch Google Sheet data and convert it to a DataFrame
def fetch_google_sheet():#(sheet_url):
    csv_url = url_csv #sheet_url.replace('/edit#gid=', '/export?format=csv&gid=')
    response = requests.get(csv_url)
    response.raise_for_status()  # Ensure the request was successful
    df = pd.read_csv(io.StringIO(response.text))
    return df

client = MongoClient('mongodb+srv://{}:{}@users.eeaisqu.mongodb.net/'.format(os.environ.get('mongo_username'),os.environ.get('mongo_password')))
db = client['tech_app_test']

# Function to convert DataFrame to CSV and provide download link
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

df = fetch_google_sheet()
# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

aws_access_key_id = os.environ.get('aws_access_key_id')
aws_secret_access_key = os.environ.get('aws_secret_access_key')
bucket_name = r'streamlit-fintech-app'
s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

# Function to list files in S3 bucket
def list_s3_files(bucket):
    try:
        response = s3.list_objects_v2(Bucket=bucket)
        if 'Contents' in response:
            return [content['Key'] for content in response.get('Contents', [])]#response['Contents']]
        else:
            return []
    except Exception as e:
        st.error(f"Error listing files: {e}")
        return []


# Function to download a file from S3
def download_s3_file(bucket, file_key, download_path):
    try:
        s3.download_file(bucket, file_key, download_path)
        return True
    except Exception as e:
        st.error(f"Error downloading {file_key}: {e}")
        return False

def save_uploaded_file(uploaded_file):
        with open(os.path.join('tempDir', uploaded_file.name), 'wb') as f:
            f.write(uploaded_file.getbuffer())
        return st.success('Saved file:{} in tempDir'.format(uploaded_file.name))



def register_user(email,username, password):
    user_data = {'email':email,'username': username, 'password': password}
    st.session_state.user_data = user_data
    st.session_state.authenticated = True
    
def authenticate_user(username, password):
    # Simulate user authentication
    client = client = MongoClient('mongodb+srv://{}:{}@users.eeaisqu.mongodb.net/'.format(os.environ.get('mongo_username'),os.environ.get('mongo_password')))
    db = client['tech_app_test']
    collection = db['staffUsers']
    user_data = collection.find_one({'username': username, 'password': password})
    if user_data:# in st.session_state:
        #if st.session_state.user_data['username'] == username and st.session_state.user_data['password'] == password:
        st.session_state.user_data = user_data
        st.session_state.authenticated = True
        #st.success("User authenticated successfully")
    else:
        st.warning("Invalid credentials")

def logout_user():
    st.session_state.authenticated = False


# User Registration and Authentication
if not st.session_state.authenticated:
    st.sidebar.title("User Authentication")
    auth_choice = st.sidebar.selectbox("Choose Action", ["Login", "Register"])

    if auth_choice == "Register":
        email = st.sidebar.text_input('email')
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Register"):
            register_user(email, username, password)
            data = {'email':email, 'username':username, 'password':password}
            json_string = json.dumps(data)
            client = client = MongoClient('mongodb+srv://{}:{}@users.eeaisqu.mongodb.net/'.format(os.environ.get('mongo_username'),os.environ.get('mongo_password')))
            db = client['tech_app_test']
            collection = db['staffUsers'] 
            result = collection.insert_one(data)

            st.success("User registered successfully")

    if auth_choice == "Login":
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            authenticate_user(username, password)
            if st.session_state.authenticated:
                st.success("User authenticated successfully")

def save_user_data_to_gcs(user_data):
    """Save user data to Google Cloud Storage"""
    # Set up Google Cloud Storage client
    client = storage.Client.from_service_account_json(r'airy-rock-395502-44a0f78f3484.json')
    bucket_name = r'https://console.cloud.google.com/storage/browser/test_app_fintech_streamlit/'  # Replace with your bucket name
    bucket = client.bucket(bucket_name)
    
    # Create a blob and upload the user data
    blob = bucket.blob(f"users/{user_data['username']}.json")
    blob.upload_from_string(data=json.dumps(user_data), content_type='application/json')

# End User Section
if st.session_state.authenticated:
    st.sidebar.button("Logout", on_click=logout_user)

    st.title("Capital")

    # Chatbot Integration
    st.subheader("Chat with our AI")
    url = 'https://chatgpt.com/g/g-VP9UTAz2c-financial-analyst-assistant' #'https://chatgpt.com/g/g-zL5o4nHMj-customer-experience'
    user_input = st.text_area("Puedes chatear con nuestro asistente: ")
    
    if st.button("Send", key=1):
        
        #url = 'https://chatgpt.com/g/g-VP9UTAz2c-financial-analyst-assistant'

        response = openai.chat.completions.create(
            model= 'gpt-4',
            stream=False,
            messages=[
            {"role": "system", "content": url},
            {'role':'user','content':user_input}
            ]
        )
        response = response.choices[0].message.content
        #response = openai.Completion.create(
        #    engine="text-davinci-002",
        #    prompt=user_input,
        #    max_tokens=150
        #)
        #st.text_area("GPT Response:", response)#response.choices[0].text)
        response_placeholder = st.empty()
        response_placeholder.write(response)

        #st.experimental_rerun()

# Backoffice Section
if st.session_state.authenticated:
    st.title("Backoffice Section")

    # Display registered users
    if 'user_data' in st.session_state:
        st.subheader("Registered Users")
        # Retrieve data from MongoDB
        collection = db['users']
        data = list(collection.find())

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Drop the MongoDB default '_id' field if present
        if '_id' or 'password' in df.columns:
            df = df.drop('_id', axis=1)
            df = df.drop('password', axis=1)

        st.dataframe(df)
        #st.write(pd.DataFrame([st.session_state.user_data]))

    # Streamlit UI
    st.title("File Browser")

    # List files in S3 bucket
    files = list_s3_files(bucket_name)
    if files:
        #st.write("Files in bucket:")
        selected_files = st.multiselect("Select files to download", files)

        if st.button("Download Selected Files"):
            if not os.path.exists(r"Downloads"):
                os.makedirs(r"Downloads")
            
            for file_key in selected_files:
                download_path = os.path.join(r"Downloads", os.path.basename(file_key))
                if download_s3_file(bucket_name, file_key, download_path):
                    st.success(f"Downloaded {file_key} to {download_path}")
                else:
                    st.error(f"Failed to download {file_key}")
    else:
        st.write("No files found in the bucket.")

    # Display status of uploaded files
    #st.subheader("Files Available")
    #files = os.listdir(".")
    #file_status = {"File Name": files, "Status": ["Uploaded"] * len(files)}
    #files=[]
    #st.write(pd.DataFrame(files))

    # API Integration for file analysis
    #st.subheader("File Analysis")
    #api_choice = st.selectbox("Choose Action", ["Download", "Analyze"])

    #if api_choice == "Download":
    #    selected_file = st.selectbox("Select File", files)
    #    file_path = os.path.join('', selected_file)
    #    with open(file_path, "rb") as file:
    #        st.download_button(
    #            label=f"Download {selected_file}",
    #            data=file,
    #            file_name=selected_file
    #        )

    #if api_choice == "Analyze":
    #    selected_file = st.selectbox("Select File", files)
        # Placeholder for file analysis using an API
    #    st.write(f"Analyzing {selected_file}...")