from huggingface_hub import login, hf_hub_download  # ✅ make sure 'login' is imported

############################################################
#
# This is a script to download a model from Hugging Face Hub
#
# username : NANDU1234      passwd : Kupmanduk1234@
#
# Get the token from here : https://huggingface.co/settings/tokens
#               Click 'create new token'
#
# Run this script as follows:
#
#       C:\Users\nandu\AppData\Local\Programs\Python\Python311\python.exe .\llm_model_download.py
#
#
# Keep the models here:
#
#       C:\Users\nandu\.cache\gpt4all\
#
# Following models are downloaded till Jule-09-2025:
#
#           mistral-7b-instruct-v0.1.Q4_0.gguf
#           tinyllama-1.1b-chat-v1.0.Q4_0.gguf
############################################################


# Step 1: Login with your token - uncomment below code-line.
# login(YOUR_TOKEN_HERE)  # Replace with your actual token

# Step 2: Download the model file
local_path = hf_hub_download(
    repo_id="TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
    filename="tinyllama-1.1b-chat-v1.0.Q4_0.gguf",
    local_dir="models"
)

print(f"✅ Model downloaded to: {local_path}")
