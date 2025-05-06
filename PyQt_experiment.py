from PyQt5.QtWidgets import QApplication, QLabel

from gpt4all import GPT4All

response = ''

# Create a context manager, loads automatically
with GPT4All("mistral-7b-instruct-v0.1.Q4_0.gguf") as model:
    response = model.generate("Read the file power3.txt and give all net names.")
    print(response)


print(response)

model.close()

app = QApplication([])

# label = QLabel("Hello, PyQt!")
label = QLabel(response)

label.show()
app.exec_()