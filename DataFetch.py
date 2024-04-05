import tkinter as tk
from tkinter import messagebox
import requests
class AccountDataRetrieverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI System Selection")
        self.create_button("Replika", self.retrieve_replika_data)
        self.create_button("ChatGPT", self.retrieve_chatgpt_data)
        self.create_button("Gemini", self.retrieve_gemini_data)
        self.create_button("AIStudio", self.retrieve_aistudio_data)
    def create_button(self, text, command):
        btn = tk.Button(self.root, text=text, command=command)
        btn.pack(pady=5)
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
def fetch_facebook_messages(access_token):
    url = 'https://graph.facebook.com/me/messages'
    params = {
        'access_token': access_token,
        'fields': 'messages'
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        messages = response.json().get('messages', [])
        return messages
    else:
        return []
if __name__ == '__main__':
    access_token = 'YOUR_FACEBOOK_ACCESS_TOKEN'
    facebook_messages = fetch_facebook_messages(access_token)
    print(facebook_messages)
import requests
def fetch_facebook_messages(access_token):
    url = 'https://graph.facebook.com/v13.0/me/messages'
    params = {
        'access_token': access_token,
        'fields': 'messages'
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        messages = response.json().get('messages', [])
        return messages
    else:
        return []
from .DataFetch import fetch_facebook_messages
def import_facebook_messages(request):
    if request.method == 'POST':
        access_token = request.POST.get('access_token')
        messages = fetch_facebook_messages(access_token)
        return HttpResponse('Messages imported successfully!')
    else:
        return HttpResponseBadRequest('Invalid request method')
<!DOCTYPE html>
<html>
<head>
    <title>CatChat</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="/static/scripts.js"></script>
</head>
<body>
    <h1>Welcome to CatChat</h1>
    <button id="import-facebook">Import from Facebook</button>
    <!-- Add more buttons/icons for other platforms -->
</body>
</html>
$(document).ready(function() {
    $('#import-facebook').click(function() {
        var access_token = prompt('Enter your Facebook access token:');
        $.ajax({
            type: 'POST',
            url: '/import/facebook',  // URL mapped to import_facebook_messages view
            data: { access_token: access_token },
            success: function(response) {
                alert('Messages imported successfully!');
            },
            error: function(xhr, status, error) {
                alert('Failed to import messages. Please try again.');
            }
        });
    });
});
from flask import Flask, request, jsonify
app = Flask(__name__)
@app.route('/import/facebook', methods=['POST'])
def import_facebook_messages():
    access_token = request.json.get('access_token')
    return jsonify({'message': 'Messages imported successfully'})
if __name__ == '__main__':
    app.run(debug=True)