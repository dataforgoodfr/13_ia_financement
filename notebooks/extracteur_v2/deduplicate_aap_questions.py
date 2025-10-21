from fuzzywuzzy import fuzz
import json
from sentence_transformers import SentenceTransformer, util
from openai import OpenAI
from pathlib import Path
import dotenv
import traceback
import sys
import time

root_path = Path(__file__).parent.resolve()

dotenv.load_dotenv("./streamlit_users_test/.env")


def print_progress_bar(questions, nb_questions_analysed):
    progress = nb_questions_analysed
    total = len(questions)
    bar_length = 40
    filled_length = int(bar_length * progress // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f"\rProgress: |{bar}| {progress}/{total} questions", end='')
    sys.stdout.flush()


def get_duplicate_with_llm(text1, text2, page_text1, page_text2):
    client = OpenAI()
        
    system_prompt="""
        You are a semantic duplicate detector. Given two input texts A and B, determine whether they express the same meaning and therefore should be considered duplicates.  

        • Your answer must include:
        1. a label: “DUPLICATE” or “NOT_DUPLICATE”
        2. a confidence score from 0.0 (no confidence) to 1.0 (maximum confidence)        

        • Consider variations such as:
        – truncation (one text is an excerpt of the other)
            -> highly probable when the pages are overlaping, like page text A [1,2], page text A [2,3],
        – paraphrase (different wording but same intent)
        – re‑ordering or added optional detail
        – synonyms, but pay attention to changes in scope or emphasis
        – differences in question verbs or focus words that alter meaning

        • Strictly label as DUPLICATE only if their core meaning and intent coincide—even if one is shorter, truncated, or worded differently.

        Output a json schema

    """
    user_prompt=f"""
        Text 1: {text1}
        Page text 1 {page_text1}

        Text 2: {text2}
        Page text 1 {page_text2}
    """

    response = client.responses.create(
        model="o4-mini",
        input=[
            {
                    "role": "system",
                    "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        reasoning={
            "effort": "low"
        },             
    )

    return response.output_text
    
def detect_duplicate_questions_v2(questions, threshold=90):

    questions_analysed=[]
    trace_questions_analysed=[]
    duplicates=[]
    nb_candidates_duplicates=0
    nb_duplicates=0
    for q in questions:
        if not questions_analysed:
            questions_analysed.append(q)
        else:
            prev_q = questions_analysed[-1]
            similarity = fuzz.token_set_ratio(q['question'][:200], prev_q['question'][:200])            
            
            

            if similarity >= threshold: 
                prev_q["fuzzy_eval"]=similarity     
                _llm_eval=get_duplicate_with_llm( q["question"][:200], prev_q["question"][:200], q["page"], prev_q["page"])
                
                try:
                    llm_eval=json.loads(_llm_eval)
                    prev_q["llm_eval"]=llm_eval
                    if llm_eval["label"]=='DUPLICATE':

                        prev_q["duplicate_detected"]=True            
                        prev_q["duplicate_question"]=q["question"]
                        duplicates.append(prev_q)

                        nb_duplicates+=1

                        #print(f"======\nNb true duplicates:{nb_duplicates}")
                except Exception as e:
                    print(_llm_eval)
                    print(f"llm call: {e}")
                

                questions_analysed.append(q)
                

                nb_candidates_duplicates+=1
                #print(f"=====\nNb candidates duplicates: {nb_candidates_duplicates}")


            else:
                questions_analysed.append(q)
            
            print_progress_bar(questions, questions_analysed)


def detect_duplicate_questions_v3(questions, threshold=80):

    def keep_longest_duplicate(q, prev_q, questions_analysed, trace_questions_analysed):
        if q["question"] in trace_questions_analysed:
            return questions_analysed, trace_questions_analysed
        
        if len(q["question"])> len(prev_q["question"]):
            # prev_q["duplicate_detected"]=True          
            q["real_duplicate"]=False
            prev_q["real_duplicate"]=True
            questions_analysed.append(q)
            trace_questions_analysed.append(q["question"])

        elif len(prev_q["question"])> len(q["question"]):
            prev_q["real_duplicate"]=False
            q["real_duplicate"]=True
            questions_analysed.append(prev_q)         
            trace_questions_analysed.append(prev_q["question"])
        elif len(prev_q["question"])== len(q["question"]):
            q["real_duplicate"]=False
            prev_q["real_duplicate"]=False

            questions_analysed.append(q)   
            trace_questions_analysed.append(q["question"])

        return questions_analysed, trace_questions_analysed

    
    questions_analysed=[]
    trace_questions_analysed=[]
    duplicates=[]
    nb_candidates_duplicates=0
    nb_duplicates=0
    nb_questions_analysed=0
    
    for q in questions:
        if not questions_analysed:
            questions_analysed.append(q)
        else:
            # gather the list of questions from previous page to perform check against
            if q["page"][0]>0:
                prev_page_num=q["page"][0]-1
                prev_page_questions=[_q for _q in questions if _q["page"][0]==prev_page_num]
            else:
                prev_page_num=None

            # when we are at the first page, add questions without similarity check
            if prev_page_num==None:
                questions_analysed.append(q)
            else:
                # when have an history of prev pages, perform the similarity check
                for prev_q in prev_page_questions:
                    
                    similarity = fuzz.token_set_ratio(q['question'][:200], prev_q['question'][:200])            
                

                    if similarity >= threshold:
                        
                        q["analyse"]={}
                        q["analyse"]["fuzzy_eval"]=similarity     
                        _llm_eval=get_duplicate_with_llm( q["question"][:200], prev_q["question"][:200], q["page"], prev_q["page"])
                
                        
                        try:
                            llm_eval=json.loads(_llm_eval)
                            q["analyse"]["llm_eval"]=llm_eval
                            q["analyse"]["candidate_duplicate"]=prev_q["question"]
                            if llm_eval["label"]=='DUPLICATE':                                

                                # q["real_duplicate"]=True
                                # prev_q["real_duplicate"]=True
                                duplicates.append(q)

                                nb_duplicates+=1

                                #print(f"======\nNb true duplicates:{nb_duplicates}")
                        except Exception as e:
                            print(_llm_eval)
                            print(f"llm call: {e}")
                        
                        # s'assurer de conserver la question non tronquée (+ grande taille de car)
                        questions_analysed, trace_questions_analysed= keep_longest_duplicate(q, prev_q, questions_analysed, trace_questions_analysed)

                    # elif similarity>=98:
                    #     q["real_duplicate"]=True
                    #     questions_analysed= keep_longest_duplicate(q, prev_q, questions_analysed)

                        

                        nb_candidates_duplicates+=1
                        #print(f"=====\nNb candidates duplicates: {nb_candidates_duplicates}")


                    else:
                        
                        questions_analysed.append(q)
                        trace_questions_analysed.append(q["question"])
        nb_questions_analysed+=1
        print_progress_bar(questions, nb_questions_analysed)
            

    print(f"\n=========\nTotal nb of suspicious duplicates: {nb_candidates_duplicates}")
    print(f"Total nb of true duplicates: {nb_duplicates}\n=========")

    # questions_cleaned=[q for q in questions_analysed if "duplicate_detected" not in q]
    questions_cleaned=[]
    for el in questions_analysed:
        if "real_duplicate" not in el:
            questions_cleaned.append(el)
        # elif "real_duplicate" in el and "analyse" in el:
        elif "real_duplicate" in el and el["real_duplicate"]==False:
            # if el["analyse"]["llm_eval"]["label"].lower()=='not_duplicate':
                questions_cleaned.append(el)

    return questions_cleaned

# q1="Main Activities (max. 300 words)\nList and describe the main activities that the project will implement to achieve the above outputs and outcomes."

# q2="Main Activities (max. 300 words)\nList and describe the main activities that the project will implement to achieve the above outputs and outcomes in detail. The project breakdown should be consistent with the Logical Framework (Appendix 1)."

# print(f"full lenght:", get_duplicate_with_llm(q1, q2))
# print(f"150 car lenght:", get_duplicate_with_llm(q1[:100], q2[:150]))
# print(f"200 car lenght:", get_duplicate_with_llm(q1[:200], q2[:200]))



# 1er deduplicate grossier avec un set
# _cleaned_questions=set([q["question"] for q in questions])
# Use dict.fromkeys to preserve order while removing duplicates

def deduplicate_raw_extracted_questions(questions: list):
    """
        input: list of extracted questions with duplicates
        output: list of extracted questions free from exact duplicates
    """
    print(f"Nb total questions: {len(questions)}")

    _cleaned_questions = list(dict.fromkeys(q["question"] for q in questions))

    # récupérer les metadata
    cleaned_questions=[]
    for qc in _cleaned_questions:    
        for el in questions:
            if qc==el["question"]:
                cleaned_questions.append(el)                
                break
        
    print(f"Nb deduplicated questions: {len(cleaned_questions)}\n============")

    return cleaned_questions


def remove_duplicates_fuzz(questions, threshold=98):
    unique_questions = []
    rejected_duplicates=[]
    prefered_duplicates=[]

    for i, q1 in enumerate(questions):
        is_duplicate = False
        prefered_question=q1
        for q2 in unique_questions:
            similarity = fuzz.token_set_ratio(q1['question'], q2['question'])
            q1_len=len(q1["question"])
            q2_len=len(q2["question"])

            if similarity > threshold and q1_len==q2_len:
                is_duplicate = True
                break
            elif similarity > threshold and q1_len>q2_len:
                prefered_question=q1       
                if q2["question"] not in rejected_duplicates and q1["question"] not in prefered_duplicates:
                    rejected_duplicates.append(q2["question"])
                    prefered_duplicates.append(prefered_question["question"])

                is_duplicate = True
                break                
            elif similarity > threshold and q2_len>q1_len:
                prefered_question=q2
                if q2["question"] not in rejected_duplicates and q1["question"] not in prefered_duplicates:
                    rejected_duplicates.append(q1["question"])
                    prefered_duplicates.append(prefered_question["question"])

                is_duplicate = True
                break                
            

        if not is_duplicate:
            unique_questions.append(q1)
            
    # drop rejected duplicates, replace them by prefered ones
    selection_duplicates=[r+"-|-"+p for r, p in zip(rejected_duplicates, prefered_duplicates)]
    selection_duplicates=list(set(selection_duplicates))
    selection_duplicates=[el.split("-|-") for el in selection_duplicates]


    final_unique_questions=[]
    for fq in unique_questions:
        is_duplicate = False
        for el in selection_duplicates:
            reject=el[0]
            prefer=el[1]

            if fq["question"]== reject:
                fq["question"]=prefer
                final_unique_questions.append(fq)
                is_duplicate = True
                break
        if not is_duplicate:
            final_unique_questions.append(fq)
            
            


    return unique_questions


# with open('./extracted_questions/extracted_raw_questions.json', 'r', encoding='utf-8') as f:
#     questions = json.load(f)

# deduplicated_questions=deduplicate_raw_extracted_questions(questions)



# cleaned_questions = detect_duplicate_questions_v3(deduplicated_questions)

# save_path=root_path/'extracted_questions/set-questions-cleaned-all.json'
# with open(save_path, 'w', encoding='utf-8') as f:
#     json.dump(cleaned_questions, f, ensure_ascii=False, indent=2)

# t=time.time()
# cleaned_questions=remove_duplicates_fuzz(cleaned_questions)
# print(f"time remove_duplicates_fuzz ---> {time.time()-t}")

# save_path=root_path/'extracted_questions/set-questions-cleaned.json'
# with open(save_path, 'w', encoding='utf-8') as f:
#     json.dump(cleaned_questions, f, ensure_ascii=False, indent=2)

