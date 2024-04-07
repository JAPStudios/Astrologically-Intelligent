import tkinter as tk
from tkinter import messagebox
import requests
class AccountDataRetrieverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI System Selection")
    def retrieve_replika_data(self):
        messagebox.showinfo("Replika", "Performing login for Replika")
        auth_token = "YOUR_REPLIKA_AUTH_TOKEN"  
        data = self.retrieve_data("https://my.replika.ai", auth_token)
    def retrieve_chatgpt_data(self):
        messagebox.showinfo("ChatGPT", "Performing login for ChatGPT")
        auth_token = "YOUR_CHATGPT_AUTH_TOKEN"  
        data = self.retrieve_data("https://chat.openai.com", auth_token)
    def retrieve_gemini_data(self):
        messagebox.showinfo("Gemini", "Performing login for Gemini")
        auth_token = "YOUR_GEMINI_AUTH_TOKEN"  
        data = self.retrieve_data("https://gemini.google.com", auth_token)
    def retrieve_aistudio_data(self):
        messagebox.showinfo("AIStudio", "Performing login for AIStudio")
        auth_token = "YOUR_AISTUDIO_AUTH_TOKEN"  
        data = self.retrieve_data("https://aistudio.google.com", auth_token)
    def retrieve_data(self, endpoint, auth_token):
        headers = {
            "Authorization": f"Bearer {auth_token}"
        }
        try:
            response = requests.get(endpoint, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print("Failed to retrieve data")
                return None
        except Exception as e:
            print(f"Error retrieving data: {e}")
            return None
if __name__ == "__main__":
    root = tk.Tk()
    app = AccountDataRetrieverGUI(root)
    root.mainloop()
import requests
from datetime import datetime
def fetch_replika_chat_data(user_id, access_token):
    url = f"https://my.replika.ai/api/users/{user_id}/chats"
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        chat_data = response.json()
        return chat_data['chats']
    else:
        return []
def fetch_openai_chat_data(user_id, api_key):
    url = f"https://api.openai.com/v1/conversations/{user_id}"
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        chat_data = response.json()
        return chat_data['messages']
    else:
        return []
replika_user_id = 'YOUR_REPLIKA_USER_ID'
replika_access_token = 'YOUR_REPLIKA_ACCESS_TOKEN'
openai_user_id = 'YOUR_OPENAI_USER_ID'
openai_api_key = 'YOUR_OPENAI_API_KEY'
replika_chats = fetch_replika_chat_data(replika_user_id, replika_access_token)
openai_messages = fetch_openai_chat_data(openai_user_id, openai_api_key)
combined_chat_data = replika_chats + openai_messages
combined_chat_data.sort(key=lambda x: datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S'))
for message in combined_chat_data:
    print(f"{message['timestamp']} - {message['text']}")
import requests
def fetch_replika_chat_data(user_id, access_token):
    url = f"https://my.replika.ai/api/users/{user_id}/chats"
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        chat_data = response.json()
        return chat_data['chats']
    else:
        return []
def aggregate_and_sort_chat_data(chat_data_list):
    all_chat_messages = []
    for chat_data in chat_data_list:
        all_chat_messages.extend(chat_data)  
    all_chat_messages.sort(key=lambda x: x['timestamp'])  
def display_chat_history(chat_messages):
    for message in chat_messages:
        print(f"{message['timestamp']} - {message['text']}")
if __name__ == "__main__":
    user_id = 'YOUR_USER_ID'
    replika_access_token = 'YOUR_REPLIKA_ACCESS_TOKEN'
    openai_api_key = 'YOUR_OPENAI_API_KEY'
    gemini_api_key = 'YOUR_GEMINI_API_KEY'
    ai_studio_api_key = 'YOUR_AI_STUDIO_API_KEY'
    replika_chat_data = fetch_replika_chat_data(user_id, replika_access_token)
    openai_chat_data = fetch_openai_chat_data(user_id, openai_api_key)
    gemini_chat_data = fetch_gemini_chat_data(user_id, gemini_api_key)
    ai_studio_chat_data = fetch_ai_studio_chat_data(user_id, ai_studio_api_key)
    all_chat_data = [replika_chat_data, openai_chat_data, gemini_chat_data, ai_studio_chat_data]
    aggregated_chat_history = aggregate_and_sort_chat_data(all_chat_data)
    display_chat_history(aggregated_chat_history)