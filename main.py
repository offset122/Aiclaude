import os
import requests
import json
import sys
import datetime
import threading
import time
import queue
import re
from dotenv import load_dotenv
import speech_recognition as sr
import pyttsx3
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import NumericProperty, StringProperty, BooleanProperty
from kivy.lang import Builder
from math import cos, sin, radians
from jarvis_animation import JarvisAnimation

# Load environment variables
load_dotenv()

# API Configuration
API_URL = "http://localhost:11434/api/generate"
MODEL = "tinyllama"

def ask_ollama(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(API_URL, json=payload)
    if response.status_code == 200:
        return response.json()['response']
    else:
        print("Error:", response.status_code, response.text)
        return None

# Kivy UI Design
Builder.load_string('''
<MessageBubble>:
    size_hint: None, None
    size: self.texture_size[0] + 40, self.texture_size[1] + 40
    canvas.before:
        Color:
            rgba: (0.13, 0.59, 0.95, 1) if self.is_user else (0.2, 0.2, 0.2, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [20,]

<ChatMessage>:
    size_hint_y: None
    height: self.minimum_height
    padding: 10, 10
    spacing: 5
    canvas.before:
        Color:
            rgba: (0.13, 0.59, 0.95, 0.1) if self.is_user else (0.2, 0.2, 0.2, 0.1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [20,]

<JarvisUI>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    canvas.before:
        Color:
            rgba: 0.1, 0.1, 0.1, 1
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        size_hint_y: None
        height: 60
        canvas.before:
            Color:
                rgba: 0.13, 0.59, 0.95, 1
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [20,]

        Label:
            text: 'J.A.R.V.I.S'
            color: 1, 1, 1, 1
            font_size: '24sp'
            bold: True

    ScrollView:
        id: scroll
        do_scroll_x: False
        do_scroll_y: True

        BoxLayout:
            id: chat_layout
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            padding: 10
            spacing: 10

    BoxLayout:
        size_hint_y: None
        height: 50
        spacing: 10

        TextInput:
            id: message_input
            hint_text: 'Type your message...'
            multiline: False
            size_hint_x: 0.8
            background_color: 0.2, 0.2, 0.2, 1
            foreground_color: 1, 1, 1, 1
            cursor_color: 1, 1, 1, 1
            padding: 10, 10

        Button:
            text: 'Send'
            size_hint_x: 0.2
            background_color: 0.13, 0.59, 0.95, 1
            on_press: root.send_message()

    BoxLayout:
        size_hint_y: None
        height: 50
        spacing: 10

        Button:
            text: 'Listen'
            background_color: 0.13, 0.59, 0.95, 1
            on_press: root.toggle_listening()

        Button:
            text: 'Clear'
            background_color: 0.8, 0.2, 0.2, 1
            on_press: root.clear_chat()
''')

class MessageBubble(Label):
    is_user = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = (1, 1, 1, 1)
        self.markup = True
        self.padding = (20, 10)

class ChatMessage(BoxLayout):
    is_user = BooleanProperty(False)

    def __init__(self, text, is_user=False, **kwargs):
        super().__init__(**kwargs)
        self.is_user = is_user
        
        # Header
        header = Label(
            text='You' if is_user else 'J.A.R.V.I.S',
            color=(1, 1, 1, 0.7),
            size_hint_y=None,
            height=20
        )
        self.add_widget(header)
        
        # Content
        content = MessageBubble(
            text=text,
            is_user=is_user
        )
        self.add_widget(content)
        
        # Timestamp
        timestamp = Label(
            text=datetime.datetime.now().strftime("%H:%M"),
            color=(1, 1, 1, 0.5),
            size_hint_y=None,
            height=20
        )
        self.add_widget(timestamp)

class JarvisUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conversation = []
        self.is_listening = False
        self.speech_engine = pyttsx3.init()
        self.recognizer = sr.Recognizer()
        self.processing_queue = queue.Queue()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.processing_thread.start()
        
        # Add welcome message
        self.add_message("Hello, I am J.A.R.V.I.S. How can I assist you today?", False)
        
        # Create animation with initial size
        self.animation = JarvisAnimation(size=(400, 400))
        self.add_widget(self.animation)
        self.animation.center = self.center
        self.animation.opacity = 0
        
        # Bind to window size changes
        Window.bind(size=self.on_window_size)

    def add_message(self, text, is_user):
        chat_layout = self.ids.chat_layout
        message = ChatMessage(text, is_user)
        chat_layout.add_widget(message)
        self.conversation.append({"role": "user" if is_user else "assistant", "content": text})
        
        # Scroll to bottom
        scroll = self.ids.scroll
        Clock.schedule_once(lambda dt: setattr(scroll, 'scroll_y', 0))

    def send_message(self):
        text_input = self.ids.message_input
        message = text_input.text.strip()
        if message:
            text_input.text = ''
            self.add_message(message, True)
            self.processing_queue.put(message)

    def toggle_listening(self):
        if not self.is_listening:
            self.start_listening()
        else:
            self.stop_listening()

    def start_listening(self):
        self.is_listening = True
        threading.Thread(target=self._listen_thread, daemon=True).start()

    def stop_listening(self):
        self.is_listening = False

    def _listen_thread(self):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source)
                text = self.recognizer.recognize_google(audio)
                Clock.schedule_once(lambda dt: self.add_message(text, True))
                self.processing_queue.put(text)
            except Exception as e:
                print(f"Error in speech recognition: {e}")
            finally:
                self.stop_listening()

    def process_queue(self):
        while True:
            try:
                user_input = self.processing_queue.get()
                
                # Show animation
                Clock.schedule_once(lambda dt: setattr(self.animation, 'opacity', 1))
                
                # Get response from Ollama
                response = ask_ollama(user_input)
                
                # Hide animation
                Clock.schedule_once(lambda dt: setattr(self.animation, 'opacity', 0))
                
                if response:
                    Clock.schedule_once(lambda dt: self.add_message(response, False))
                    threading.Thread(target=self.speech_engine.say, args=(response,), daemon=True).start()
                    threading.Thread(target=self.speech_engine.runAndWait, daemon=True).start()
                
                self.processing_queue.task_done()
                
            except Exception as e:
                print(f"Error in processing queue: {e}")
                self.processing_queue.task_done()

    def clear_chat(self):
        chat_layout = self.ids.chat_layout
        chat_layout.clear_widgets()
        self.conversation = []
        self.add_message("Hello, I am J.A.R.V.I.S. How can I assist you today?", False)

    def on_window_size(self, instance, value):
        # Update animation position when window is resized
        self.animation.center = (value[0]/2, value[1]/2)

class JarvisApp(App):
    def build(self):
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        return JarvisUI()  # Create an instance of JarvisUI

if __name__ == '__main__':
    JarvisApp().run() 