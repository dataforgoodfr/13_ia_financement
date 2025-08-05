from fuzzywuzzy import fuzz
import json
from sentence_transformers import SentenceTransformer, util
from openai import OpenAI
from pathlib import Path
import dotenv


dotenv.load_dotenv("./streamlit_local/.env")

embedding_models={
    "granite": SentenceTransformer("ibm-granite/granite-embedding-278m-multilingual",trust_remote_code=True, device="cpu"),
    # "snowflake": SentenceTransformer('Snowflake/snowflake-arctic-embed-m-v2.0',trust_remote_code=True, device="cpu"),
    "minilm-l12-v2-multi": SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", trust_remote_code=True, device="cpu"),
    "e5-large": SentenceTransformer("intfloat/multilingual-e5-large-instruct", trust_remote_code=True, device="cpu")
}

def get_similarity(model_name, text1, text2):
    model = embedding_models[model_name]    

    # encode queries and passages
    text1_embeddings = model.encode([text1], normalize_embeddings=True)
    text2_embeddings = model.encode([text2], normalize_embeddings=True)

    # calculate cosine similarity
    return util.cos_sim(text1_embeddings, text2_embeddings)


def get_duplicate_with_llm(text1, text2):
    client = OpenAI()
        
    system_prompt="""
        You are a semantic duplicate detector. Given two input texts A and B, determine whether they express the same meaning and therefore should be considered duplicates.  

        • Your answer must include:
        1. a label: “DUPLICATE” or “NOT_DUPLICATE”
        2. a confidence score from 0.0 (no confidence) to 1.0 (maximum confidence)        

        • Consider variations such as:
        – truncation (one text is an excerpt of the other)
        – paraphrase (different wording but same intent)
        – re‑ordering or added optional detail
        – synonyms, but pay attention to changes in scope or emphasis
        – differences in question verbs or focus words that alter meaning

        • Strictly label as DUPLICATE only if their core meaning and intent coincide—even if one is shorter, truncated, or worded differently.

        Output a json schema

    """
    user_prompt=f"""
        Text 1: {text1}
        Text 2: {text2}
    """

    response = client.chat.completions.create(
        model="o4-mini",
        messages=[
            {
                    "role": "system",
                    "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],        
    )

    return response.choices[0].message.content
    
def detect_duplicate_questions_v2(questions, threshold=80):
    questions_analysed=[]
    duplicates=[]
    for q in questions:
        if not questions_analysed:
            questions_analysed.append(q)
        else:
            prev_q = questions_analysed[-1]
            similarity = fuzz.token_set_ratio(q['question'][:200], prev_q['question'][:200])            
            
            

            if similarity >= threshold:
                # tag                       
                similarity_granite=get_similarity("granite", q['question'][:200], prev_q['question'][:200])        

                prev_q["similarity_fuzz"]=similarity     
                prev_q["similarity_granite"]=similarity_granite
                # prev_q["similarity_snowflake"]=get_similarity("snowflake", q['question'][:200], prev_q['question'][:200])                             
                prev_q["minilm-l12-v2-multi"]=get_similarity("minilm-l12-v2-multi", q["question"], prev_q["question"])
                prev_q["e5-large"]=get_similarity("e5-large", q["question"], prev_q["question"])
                prev_q["llm"]=get_duplicate_with_llm( q["question"], prev_q["question"])
                prev_q["duplicate_detected"]=True            
                prev_q["duplicate_question"]=q["question"]
                duplicates.append(prev_q)
                

                questions_analysed.append(q)
                print(f"======\nduplicate:")
                print(prev_q)
                print(f"======\n:")

            else:
                questions_analysed.append(q)

    questions_cleaned=[q for q in questions_analysed if "duplicate_detected" not in q]
    return questions_cleaned

def detect_duplicate_questions_v1(questions, threshold=80):
    cleaned = []

    for q in questions:
        if not cleaned:
            cleaned.append(q)
        else:
            prev_q = cleaned[-1]
            similarity = fuzz.token_set_ratio(q['question'], prev_q['question'])
            q["similarity_fuzz"]=similarity

            if similarity >= threshold:
                # Replace with the longer question
                if len(q['question']) > len(prev_q['question']):                    
                    cleaned[-1] = q
            else:
                cleaned.append(q)

    return cleaned


with open('extracted_questions-v3.json', 'r', encoding='utf-8') as f:
    questions = json.load(f)



cleaned_questions = detect_duplicate_questions_v2(questions)

# Afficher le résultat
print("\nQuestions cleaned")
for q in cleaned_questions:
    print("Question:", q)
          
    print("\n-------\n")