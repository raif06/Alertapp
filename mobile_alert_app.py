import requests
import webbrowser
import urllib.parse
import threading
import smtplib
from email.message import EmailMessage
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView


EMAIL = "parveenparveen4152@gmail.com"
APP_PASSWORD = "nqkvkttiqbvnjkzd"

SAVE_FILE = "saved_papers.txt"
FAV_FILE = "favorites.txt"


class MobileAlert(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)

        self.page_size = 10
        self.start_index = 0
        self.current_query = ""
        self.year_filter = ""

        self.add_widget(Label(text="Research Paper Alert",
                              size_hint=(1, 0.08)))

        self.search_input = TextInput(
            hint_text="Enter topic",
            multiline=False,
            size_hint=(1, 0.08)
        )
        self.search_input.bind(on_text_validate=self.start_search)
        self.add_widget(self.search_input)

        self.year_input = TextInput(
            hint_text="Filter by year (optional)",
            multiline=False,
            size_hint=(1, 0.06)
        )
        self.add_widget(self.year_input)

        search_btn = Button(text="Search Papers",
                            size_hint=(1, 0.08))
        search_btn.bind(on_press=self.start_search)
        self.add_widget(search_btn)

        saved_btn = Button(text="View Saved Papers",
                           size_hint=(1, 0.06))
        saved_btn.bind(on_press=self.show_saved_papers)
        self.add_widget(saved_btn)

        fav_btn = Button(text="View Favorites",
                         size_hint=(1, 0.06))
        fav_btn.bind(on_press=self.show_favorites)
        self.add_widget(fav_btn)

        self.page_label = Label(text="Page: 1",
                                size_hint=(1, 0.05))
        self.add_widget(self.page_label)

        self.loading_label = Label(text="",
                                   size_hint=(1, 0.04))
        self.add_widget(self.loading_label)

        self.scroll = ScrollView(size_hint=(1, 0.41))

        self.result_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=10,
            padding=10
        )
        self.result_layout.bind(
            minimum_height=self.result_layout.setter('height')
        )

        self.scroll.add_widget(self.result_layout)
        self.add_widget(self.scroll)

        nav_layout = BoxLayout(size_hint=(1, 0.08))

        prev_btn = Button(text="Previous")
        prev_btn.bind(on_press=self.prev_page)
        nav_layout.add_widget(prev_btn)

        next_btn = Button(text="Next")
        next_btn.bind(on_press=self.next_page)
        nav_layout.add_widget(next_btn)

        self.add_widget(nav_layout)

    # ---------- EMAIL ----------
    def send_email(self, content):
        if not content:
            return

        msg = EmailMessage()
        msg["Subject"] = "Research Papers Found"
        msg["From"] = EMAIL
        msg["To"] = EMAIL
        msg.set_content(content)

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(EMAIL, APP_PASSWORD)
                smtp.send_message(msg)
        except:
            print("Email failed")

    # ---------- STORAGE ----------
    def append_file(self, file, title, link):
        with open(file, "a", encoding="utf-8") as f:
            f.write(f"{title}|{link}\n")

    def delete_file(self, file):
        open(file, "w").close()

    # ---------- FAVORITES ----------
    def add_favorite(self, title, link):
        self.append_file(FAV_FILE, title, link)

    def show_favorites(self, instance):
        self.show_file(FAV_FILE)

    # ---------- SAVED ----------
    def save_paper(self, title, link):
        self.append_file(SAVE_FILE, title, link)

    def show_saved_papers(self, instance):
        self.show_file(SAVE_FILE)

    def show_file(self, file):
        self.result_layout.clear_widgets()

        try:
            with open(file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except:
            lines = []

        if not lines:
            self.result_layout.add_widget(Label(text="Nothing saved"))
            return

        for line in lines:
            title, link = line.strip().split("|")

            btn = Button(text=title,
                         size_hint_y=None,
                         height=100,
                         text_size=(600, None),
                         halign='left',
                         valign='middle')

            btn.bind(on_press=lambda inst, l=link:
                     webbrowser.open(l))

            self.result_layout.add_widget(btn)

        del_btn = Button(text="Delete All",
                         size_hint_y=None,
                         height=40)

        del_btn.bind(on_press=lambda inst: self.delete_saved(file))
        self.result_layout.add_widget(del_btn)

    def delete_saved(self, file):
        self.delete_file(file)
        self.result_layout.clear_widgets()
        self.result_layout.add_widget(Label(text="Deleted"))

    # ---------- SEARCH ----------
    def start_search(self, instance):
        self.start_index = 0
        self.current_query = self.search_input.text.strip()
        self.year_filter = self.year_input.text.strip()
        self.fetch_results_thread()

    def next_page(self, instance):
        self.start_index += self.page_size
        self.fetch_results_thread()

    def prev_page(self, instance):
        if self.start_index >= self.page_size:
            self.start_index -= self.page_size
            self.fetch_results_thread()

    # ---------- THREAD ----------
    def fetch_results_thread(self):
        self.loading_label.text = "Loading..."
        self.result_layout.clear_widgets()
        threading.Thread(target=self.fetch_results).start()

    # ---------- FETCH ----------
    def fetch_results(self):
        encoded_query = urllib.parse.quote(self.current_query)

        url = (
            "http://export.arxiv.org/api/query?"
            f"search_query=all:{encoded_query}"
            f"&start={self.start_index}"
            f"&max_results={self.page_size}"
        )

        response = requests.get(url, timeout=10)
        entries = response.text.split("<entry>")[1:]

        results = []

        for entry in entries:
            title = self.extract_tag(entry, "title")
            pdf_link = self.extract_pdf(entry)
            published = self.extract_tag(entry, "published")

            year = published[:4] if published else ""

            if self.year_filter and year != self.year_filter:
                continue

            score = self.ai_score(title)
            results.append((score, title, pdf_link))

        results.sort(reverse=True)

        email_text = ""
        for _, t, l in results:
            email_text += f"{t}\n{l}\n\n"

        self.send_email(email_text)

        Clock.schedule_once(lambda dt: self.update_ui(results))

    # ---------- UI ----------
    def update_ui(self, results):
        self.loading_label.text = ""
        self.result_layout.clear_widgets()

        if not results:
            self.result_layout.add_widget(Label(text="No results"))
            return

        for _, title, link in results:
            btn = Button(text=title,
                         size_hint_y=None,
                         height=120,
                         text_size=(600, None),
                         halign='left',
                         valign='middle')

            btn.bind(on_press=lambda inst, l=link:
                     webbrowser.open(l))
            self.result_layout.add_widget(btn)

            save_btn = Button(text="Save Paper",
                              size_hint_y=None,
                              height=40)
            save_btn.bind(on_press=lambda inst,
                          t=title, l=link:
                          self.save_paper(t, l))
            self.result_layout.add_widget(save_btn)

            fav_btn = Button(text="Add Favorite",
                             size_hint_y=None,
                             height=40)
            fav_btn.bind(on_press=lambda inst,
                         t=title, l=link:
                         self.add_favorite(t, l))
            self.result_layout.add_widget(fav_btn)

        page_num = (self.start_index // self.page_size) + 1
        self.page_label.text = f"Page: {page_num}"

    # ---------- HELPERS ----------
    def extract_tag(self, text, tag):
        try:
            start = text.index(f"<{tag}>") + len(tag) + 2
            end = text.index(f"</{tag}>")
            return text[start:end].replace("\n", " ").strip()
        except:
            return ""

    def extract_pdf(self, text):
        try:
            part = text.split('title="pdf"')[1]
            return part.split('href="')[1].split('"')[0]
        except:
            return "https://arxiv.org"

    def ai_score(self, title):
        words = self.current_query.lower().split()
        title = title.lower()
        return sum(title.count(w) for w in words)


class MobileAlertApp(App):
    def build(self):
        return MobileAlert()


MobileAlertApp().run()
