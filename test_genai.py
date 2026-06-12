import google.genai
try:
    client = google.genai.Client()
    response = client.models.generate_content(model="gemini-2.5-flash", contents="Hi")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
