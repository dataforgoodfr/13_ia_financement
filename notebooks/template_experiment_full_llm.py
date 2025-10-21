from openai import OpenAI

# adapter à votre chargeur de doc
pdf=loader_pdf.load("pp_gapadou")

all_text=""

for page in pdf:
    all_text+=page.page_content

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="<OPENROUTER_API_KEY>",
)

completion = client.chat.completions.create(

  model="deepseek/deepseek-chat-v3-0324:free",
  messages=[
    {
      "role": "system",
      "content": """
        
            Answer the question based **only** on the provided context.  

            - If the context contains enough information to provide a complete or partial answer, use it to formulate a detailed and factual response.  
            - If the context lacks relevant information, respond with: "I don't know."  


            ### **Answer:**  
            Provide a clear, factual, and well-structured response based on the available context. Avoid speculation or adding external knowledge.  
      """
    },
    {
      "role": "user",
      "content": all_text
    },
    {
      "role": "user",
      "content": "Quel est le nom du projet ?"
    }    
  ]
)

response = completion.choices[0].message.content

# modeles frontière
# openai/gpt-5
# openai/o3-pro
# mistralai/magistral-medium-2506
# mistralai/mistral-medium-3.1
# anthropic/claude-opus-4.1
# x-ai/grok-4
# google/gemini-2.5-pro
# meta-llama/llama-4-maverick
# deepseek/deepseek-chat-v3-0324
# qwen/qwen3-235b-a22b-2507
# moonshotai/kimi-k2