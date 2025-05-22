from kivy.uix.widget import Widget
from kivy.graphics import Ellipse, Color
from kivy.properties import NumericProperty
from kivy.clock import Clock
from kivy.lang import Builder

# Simplified Animation UI Design
Builder.load_string('''
<JarvisAnimation>:
    canvas:
        Color:
            rgba: 0, 1, 1, 0.5
        Ellipse:
            pos: self.center_x - 100, self.center_y - 100
            size: 200, 200
''')

class JarvisAnimation(Widget):
    def __init__(self, **kwargs):
        super(JarvisAnimation, self).__init__(**kwargs)
        self._clock_event = None
        self._start_animation()
        
    def _update(self, dt):
        try:
            self.canvas.clear()
            with self.canvas:
                Color(0, 1, 1, 0.5)
                Ellipse(pos=(self.center_x - 100, self.center_y - 100), size=(200, 200))
        except Exception as e:
            print(f"Error in _update: {e}")
            
    def _start_animation(self):
        try:
            self._stop_animation()
            self._clock_event = Clock.schedule_interval(self._update, 1/30)
        except Exception as e:
            print(f"Error in _start_animation: {e}")
    
    def _stop_animation(self):
        try:
            if self._clock_event:
                self._clock_event.cancel()
                self._clock_event = None
        except Exception as e:
            print(f"Error in _stop_animation: {e}")
    
    def on_parent(self, *args):
        if not self.parent:
            self._stop_animation()
    
    def __del__(self):
        self._stop_animation()

if __name__ == '__main__':
    from kivy.app import App
    from kivy.core.window import Window
    
    class TestApp(App):
        def build(self):
            Window.clearcolor = (0.1, 0.1, 0.1, 1)
            return JarvisAnimation(size=(400, 400))
    
    TestApp().run() 