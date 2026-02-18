import tkinter as tk
import requests
import threading
import time
import webbrowser

seen = set()
running = False


def open_link(event):
    webbrowser.open(event.widget.cget("text"))


def search_arxiv(topic):
    results = []
    url = f"http://export.arxiv.org/api/query?search_query=all:{topic}&start=0&max_results=5"
    response = requests.get(url).text

    entries = response.split("<entry>")
    for entry in entries[1:]:
        title = entry.split("<title>")[1].split("</title>")[0]
        link = entry.split("<id>")[1].split("</id>")[0]
        results.append(("arXiv", title.strip(), link))

    return results


def check_papers(topic):
    global running

    while running:
        papers = search_arxiv(topic)

        for source, title, link in papers:
            key = source + title

            if key not in seen:
                seen.add(key)
                add_paper(title, link)

        time.sleep(60)


def add_paper(title, link):
    frame = tk.Frame(result_frame, bg="#f0f4ff", pady=5)
    frame.pack(fill="x", padx=5, pady=3)

    tk.Label(
        frame,
        text=title,
        wraplength=500,
        justify="left",
        bg="#f0f4ff",
        font=("Arial", 10, "bold")
    ).pack(anchor="w")

    link_label = tk.Label(
        frame,
        text=link,
        fg="blue",
        cursor="hand2",
        bg="#f0f4ff"
    )
    link_label.pack(anchor="w")
    link_label.bind("<Button-1>", open_link)


def start_alert():
    global running
    topic = entry.get().lower()
    if topic == "":
        return
    running = True
    threading.Thread(target=check_papers, args=(topic,), daemon=True).start()


def stop_alert():
    global running
    running = False


# ---------- UI ----------
root = tk.Tk()
root.title("Research Paper Alert")
root.geometry("650x500")
root.configure(bg="#dde6f5")

tk.Label(root, text="Research Paper Alert",
         font=("Arial", 16, "bold"),
         bg="#dde6f5").pack(pady=10)

entry = tk.Entry(root, width=40, font=("Arial", 12))
entry.pack(pady=5)

button_frame = tk.Frame(root, bg="#dde6f5")
button_frame.pack()

tk.Button(button_frame, text="Start Alert",
          bg="#4CAF50", fg="white",
          command=start_alert).pack(side="left", padx=10)

tk.Button(button_frame, text="Stop Alert",
          bg="#f44336", fg="white",
          command=stop_alert).pack(side="left", padx=10)

canvas = tk.Canvas(root, bg="white")
canvas.pack(fill="both", expand=True, pady=10)

scrollbar = tk.Scrollbar(canvas)
scrollbar.pack(side="right", fill="y")

canvas.configure(yscrollcommand=scrollbar.set)
scrollbar.configure(command=canvas.yview)

result_frame = tk.Frame(canvas, bg="white")
canvas.create_window((0, 0), window=result_frame, anchor="nw")

def on_configure(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

result_frame.bind("<Configure>", on_configure)

root.mainloop()
