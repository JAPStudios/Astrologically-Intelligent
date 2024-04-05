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