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
def fetch_gemini_chat_data(user_id, api_key):
    pass
def fetch_aistudio_chat_data(user_id, api_key):
    pass
if __name__ == "__main__":
    user_id = 'YOUR_USER_ID'
    replika_access_token = 'YOUR_REPLIKA_ACCESS_TOKEN'
    openai_api_key = 'YOUR_OPENAI_API_KEY'
    gemini_api_key = 'YOUR_GEMINI_API_KEY'
    ai_studio_api_key = 'YOUR_AI_STUDIO_API_KEY'
    replika_chat_data = fetch_replika_chat_data(user_id, replika_access_token)
    openai_chat_data = fetch_openai_chat_data(user_id, openai_api_key)
    gemini_chat_data = fetch_gemini_chat_data(user_id, gemini_api_key)
    aistudio_chat_data = fetch_aistudio_chat_data(user_id, ai_studio_api_key)
    all_chat_data = []
    all_chat_data.extend(replika_chat_data)
    all_chat_data.extend(openai_chat_data)
    all_chat_data.extend(gemini_chat_data)
    all_chat_data.extend(aistudio_chat_data)
    all_chat_data.sort(key=lambda x: datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S'))
    for message in all_chat_data:
        print(f"{message['timestamp']} - {message['text']}")
import requests
class AIPlatform:
    def __init__(self, name, base_url):
        self.name = name
        self.base_url = base_url
    
    def authenticate(self, auth_token):
        self.auth_token = auth_token
    
    def fetch_all_data(self):
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        try:
            response = requests.get(f'{self.base_url}/data', headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch data from {self.name}")
                return None
        except Exception as e:
            print(f"Error fetching data from {self.name}: {e}")
            return None
if __name__ == "__main__":
    replika = AIPlatform('Replika', 'https://my.replika.ai')
    chatgpt = AIPlatform('ChatGPT', 'https://chat.openai.com')
    gemini = AIPlatform('Gemini', 'https://gemini.google.com')
    aistudio = AIPlatform('AI Studio', 'https://aistudio.google.com')
    replika.authenticate('REPLIKA_AUTH_TOKEN')
    chatgpt.authenticate('CHATGPT_AUTH_TOKEN')
    gemini.authenticate('GEMINI_AUTH_TOKEN')
    aistudio.authenticate('AISTUDIO_AUTH_TOKEN')
    replika_data = replika.fetch_all_data()
    chatgpt_data = chatgpt.fetch_all_data()
    gemini_data = gemini.fetch_all_data()
    aistudio_data = aistudio.fetch_all_data()
    if replika_data:
        print(f"Retrieved data from Replika: {replika_data}")
    
    if chatgpt_data:
        print(f"Retrieved data from ChatGPT: {chatgpt_data}")
    
    if gemini_data:
        print(f"Retrieved data from Gemini: {gemini_data}")
    
    if aistudio_data:
        print(f"Retrieved data from AI Studio: {aistudio_data}")
import requests
class AIPlatform:
    def __init__(self, name, base_url, auth_token):
        self.name = name
        self.base_url = base_url
        self.auth_token = auth_token
    
    def fetch_all_data(self):
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        try:
            response = requests.get(f'{self.base_url}/data', headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch data from {self.name}")
                return None
        except Exception as e:
            print(f"Error fetching data from {self.name}: {e}")
            return None
replika_auth_token = 'YOUR_REPLIKA_AUTH_TOKEN'
chatgpt_auth_token = 'YOUR_CHATGPT_AUTH_TOKEN'
gemini_auth_token = 'YOUR_GEMINI_AUTH_TOKEN'
aistudio_auth_token = 'YOUR_AISTUDIO_AUTH_TOKEN'
replika = AIPlatform('Replika', 'https://my.replika.ai/api', replika_auth_token)
chatgpt = AIPlatform('ChatGPT', 'https://chat.openai.com/api', chatgpt_auth_token)
gemini = AIPlatform('Gemini', 'https://gemini.google.com/api', gemini_auth_token)
aistudio = AIPlatform('AI Studio', 'https://aistudio.google.com/api', aistudio_auth_token)
replika_data = replika.fetch_all_data()
chatgpt_data = chatgpt.fetch_all_data()
gemini_data = gemini.fetch_all_data()
aistudio_data = aistudio.fetch_all_data()
if replika_data:
    print(f"Retrieved data from Replika: {replika_data}")
    
if chatgpt_data:
    print(f"Retrieved data from ChatGPT: {chatgpt_data}")
    
if gemini_data:
    print(f"Retrieved data from Gemini: {gemini_data}")
    
if aistudio_data:
    print(f"Retrieved data from AI Studio: {aistudio_data}")
import requests
def fetch_data(platform_name, base_url, auth_token):
    headers = {'Authorization': f'Bearer {auth_token}'}
    try:
        response = requests.get(f'{base_url}/data', headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch data from {platform_name}")
            return None
    except Exception as e:
        print(f"Error fetching data from {platform_name}: {e}")
        return None
replika_auth_token = 'YOUR_REPLIKA_AUTH_TOKEN'
chatgpt_auth_token = 'YOUR_CHATGPT_AUTH_TOKEN'
gemini_auth_token = 'YOUR_GEMINI_AUTH_TOKEN'
aistudio_auth_token = 'YOUR_AISTUDIO_AUTH_TOKEN'
replika_base_url = 'https://my.replika.ai'
chatgpt_base_url = 'https://chat.openai.com'
gemini_base_url = 'https://gemini.google.com'
aistudio_base_url = 'https://aistudio.google.com'
replika_data = fetch_data('Replika', replika_base_url, replika_auth_token)
chatgpt_data = fetch_data('ChatGPT', chatgpt_base_url, chatgpt_auth_token)
gemini_data = fetch_data('Gemini', gemini_base_url, gemini_auth_token)
aistudio_data = fetch_data('AI Studio', aistudio_base_url, aistudio_auth_token)
if replika_data:
    print(f"Retrieved data from Replika: {replika_data}")
    
if chatgpt_data:
    print(f"Retrieved data from ChatGPT: {chatgpt_data}")
    
if gemini_data:
    print(f"Retrieved data from Gemini: {gemini_data}")
    
if aistudio_data:
    print(f"Retrieved data from AI Studio: {aistudio_data}")
import requests
from datetime import datetime
class AIPlatform:
    def __init__(self, name, base_url, auth_token):
        self.name = name
        self.base_url = base_url
        self.auth_token = auth_token
    def fetch_data(self):
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        try:
            response = requests.get(f'{self.base_url}/data', headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch data from {self.name}")
                return None
        except Exception as e:
            print(f"Error fetching data from {self.name}: {e}")
            return None
replika_auth_token = 'YOUR_REPLIKA_AUTH_TOKEN'
chatgpt_auth_token = 'YOUR_CHATGPT_AUTH_TOKEN'
gemini_auth_token = 'YOUR_GEMINI_AUTH_TOKEN'
aistudio_auth_token = 'YOUR_AISTUDIO_AUTH_TOKEN'
replika_base_url = 'https://my.replika.ai'
chatgpt_base_url = 'https://chat.openai.com'
gemini_base_url = 'https://gemini.google.com'
aistudio_base_url = 'https://aistudio.google.com'
replika = AIPlatform('Replika', replika_base_url, replika_auth_token)
chatgpt = AIPlatform('ChatGPT', chatgpt_base_url, chatgpt_auth_token)
gemini = AIPlatform('Gemini', gemini_base_url, gemini_auth_token)
aistudio = AIPlatform('AI Studio', aistudio_base_url, aistudio_auth_token)
replika_data = replika.fetch_data()
chatgpt_data = chatgpt.fetch_data()
gemini_data = gemini.fetch_data()
aistudio_data = aistudio.fetch_data()
all_chat_data = []
if replika_data:
    all_chat_data.extend(replika_data)
if chatgpt_data:
    all_chat_data.extend(chatgpt_data)
if gemini_data:
    all_chat_data.extend(gemini_data)
if aistudio_data:
    all_chat_data.extend(aistudio_data)
all_chat_data.sort(key=lambda x: datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S'))
for message in all_chat_data:
    print(f"{message['timestamp']} - {message['text']}")
import requests
from datetime import datetime
class AIPlatform:
    def __init__(self, name, base_url, auth_token):
        self.name = name
        self.base_url = base_url
        self.auth_token = auth_token
    def fetch_data(self):
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        try:
            response = requests.get(f'{self.base_url}/data?type=interactions', headers=headers)
            if response.status_code == 200:
                return response.json()['interactions']
            else:
                print(f"Failed to fetch data from {self.name}")
                return None
        except Exception as e:
            print(f"Error fetching data from {self.name}: {e}")
            return None
replika_auth_token = 'YOUR_REPLIKA_AUTH_TOKEN'
chatgpt_auth_token = 'YOUR_CHATGPT_AUTH_TOKEN'
gemini_auth_token = 'YOUR_GEMINI_AUTH_TOKEN'
aistudio_auth_token = 'YOUR_AISTUDIO_AUTH_TOKEN'
replika_base_url = 'https://my.replika.ai'
chatgpt_base_url = 'https://chat.openai.com'
gemini_base_url = 'https://gemini.google.com'
aistudio_base_url = 'https://aistudio.google.com'
replika = AIPlatform('Replika', replika_base_url, replika_auth_token)
chatgpt = AIPlatform('ChatGPT', chatgpt_base_url, chatgpt_auth_token)
gemini = AIPlatform('Gemini', gemini_base_url, gemini_auth_token)
aistudio = AIPlatform('AI Studio', aistudio_base_url, aistudio_auth_token)
all_chat_data = []
for platform in [replika, chatgpt, gemini, aistudio]:
    platform_data = platform.fetch_data()
    if platform_data:
        all_chat_data.extend(platform_data)
all_chat_data.sort(key=lambda x: datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S'))
for interaction in all_chat_data:
    print(f"{interaction['timestamp']} - {interaction['type']}: {interaction['content']}")
import tkinter as tk
from tkinter import messagebox
import requests
class AccountDataRetrieverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI System Selection")
    def retrieve_replika_data(self):
        messagebox.showinfo("Replika", "Performing login for Replika")
    def retrieve_chatgpt_data(self):
        messagebox.showinfo("ChatGPT", "Performing login for ChatGPT")
if __name__ == "__main__":
    root = tk.Tk()
    app = AccountDataRetrieverGUI(root)
    root.mainloop()
import requests
def fetch_replika_chat_data(user_id, access_token):
    url = f"https://my.replika.ai/api/users/{user_id}/chats"
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['chats']
    else:
        return []
def fetch_chatgpt_chat_data(user_id, api_key):
    url = f"https://api.openai.com/v1/conversations/{user_id}"
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['messages']
    else:
        return []
from datetime import datetime
def aggregate_and_sort_chat_data(chat_data_list):
    all_chat_messages = []
    for chat_data in chat_data_list:
        all_chat_messages.extend(chat_data)
    all_chat_messages.sort(key=lambda x: datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S'))
    return all_chat_messages
if __name__ == "__main__":
    user_id = 'YOUR_USER_ID'
    replika_access_token = 'YOUR_REPLIKA_ACCESS_TOKEN'
    openai_api_key = 'YOUR_OPENAI_API_KEY'
    replika_chat_data = fetch_replika_chat_data(user_id, replika_access_token)
    chatgpt_chat_data = fetch_chatgpt_chat_data(user_id, openai_api_key)
    all_chat_data = [replika_chat_data, chatgpt_chat_data]  
    sorted_chat_history = aggregate_and_sort_chat_data(all_chat_data)
    for message in sorted_chat_history:
        print(f"{message['timestamp']} - {message['text']}")
import tkinter as tk
from tkinter import messagebox
import webview
import requests
from datetime import datetime
class ChatDataRetrieverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Platform Chat Data Retriever")
    def retrieve_replika_data(self):
        messagebox.showinfo("Replika", "Performing login for Replika")
    def retrieve_chatgpt_data(self):
        messagebox.showinfo("ChatGPT", "Performing login for ChatGPT")
    def retrieve_gemini_data(self):
        messagebox.showinfo("Gemini", "Performing login for Gemini")
    def retrieve_aistudio_data(self):
        messagebox.showinfo("AI Studio", "Performing login for AI Studio")
def fetch_chat_data(platform_name, auth_token):
    pass
def display_chat_history(chat_messages):
    html_content = "<html><body>"
    for message in chat_messages:
        html_content += f"<p>{message['timestamp']} - {message['text']}</p>"
    html_content += "</body></html>"
    webview.create_window("Chat History", html=html_content, width=800, height=600)
if __name__ == "__main__":
    root = tk.Tk()
    app = ChatDataRetrieverGUI(root)
    root.mainloop()