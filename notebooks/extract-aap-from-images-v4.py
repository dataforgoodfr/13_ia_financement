import os
import base64
import json
from pdf2image import convert_from_path
from PIL import Image
from openai import OpenAI
from datetime import datetime
import dotenv
from PyPDF2 import PdfReader
from docxtopdf import convert
import traceback
import sys
from fuzzywuzzy import fuzz
from pathlib import Path
from deduplicate_aap_questions import detect_duplicate_questions_v3, deduplicate_raw_extracted_questions, remove_duplicates_fuzz

root_path = Path(__file__).parent.resolve()

dotenv.load_dotenv("./streamlit_users_test/.env")

class PDFDescriber:
    def __init__(self):
        self.client = OpenAI()
        self.history = []
        self.questions=[]

        # suppression des instructions pour ne pas modifier les questions (effet de bord importants sur la capacité à reconsituer les questions multi pages)
        self.system_prompt="""
            I have a collection of form images that include questions in different configurations. The forms may include:

            1. **Straight and direct interrogative questions**, e.g.:
            - "Where is the project located?"
            - "Who are the target beneficiaries?"

            2. **Informational expectations presented in a descriptive (non-interrogative) style**, e.g.:
            - "Project description"
            - "Expected outcomes"

            3. **Composite prompts** that include an initial question **followed by conditional guidance, sub-questions, or multiple-choice items**. These may be styled as:
            - A Yes/No question followed by an explanation or requirement if "Yes"
            - A main prompt with a checklist of items or a detailed explanation block

            Examples:
            - "Is your project working in at least one Upper Middle-Income Country/ies (UMICs)? □ Yes □ No  
            If ‘Yes’, explain how your project meets the UMIC Assessment criteria... (Max 250 words)"

            - "Project Justification and Beneficiaries:  
            Please provide:  
            - A description of the issue...  
            - A Problem Tree..."

            When such follow-up text appears under a main prompt or Yes/No question, **group the entire content into a single extracted question item**, preserving the original structure and sub-components. **Do not split these into separate items**.

            The questions may be segmented by sections concerning the applicant **organization** or the **project** to be financed.

            The questions may spread across 2 pages, starting at the bottom of the first page, the continuing in the second page, so make sure to use the history of previous messages to rebuild the entire question.

            Your task is to process the provided images of these forms, extract all the questions (regardless of style), and output a JSON-like list of items. Each item should:

            - Represent one complete question or informational prompt
            - Preserve all relevant sub-prompts, conditional logic, and multiple-choice elements as part of the question
            - Include the corresponding `"section"` field: either `"organization"` or `"project"`
            - Preserve the order of appearance from the image

            Format:
            [
                {"question": "Full question prompt with any sub-questions or instructions", "section": "project"},
                {"question": "Another prompt...", "section": "organization"}
            ]

            Ensure that:
            - Each JSON item includes any follow-up conditions, guidance, or sub-prompts if they belong to the same logical block
            - No question should be arbitrarily split across two items
            - Maintain clarity and completeness, even if the text spans several lines or styles
            
        """

    def docx_to_pdf(self, input_path):
        # Conversion
        output_path=input_path.replace(".docx", ".pdf")
        convert(input_path, output_path)

        return output_path


    def pdf_to_image(self, pdf_path, pages_numbers, output_folder="temp"):
        """Convertit une page PDF en image"""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        images = convert_from_path(pdf_path, first_page=pages_numbers[0], last_page=pages_numbers[1], dpi=300)

        images_paths=[]
        for img, page_number in zip(images, pages_numbers):
            image_path = os.path.join(output_folder, f"page_{page_number}.jpg")
            img.save(image_path, "JPEG")
            images_paths.append(image_path)


        if len(images_paths)>1:
            assembled_images_path=self.assemble_images_vertically(
                image_path1=images_paths[0], image_path2=images_paths[1],
                num_page_1=pages_numbers[0], num_page_2=pages_numbers[1]    
            )
        else:
            assembled_images_path=images_paths[0]

        return assembled_images_path

    def assemble_images_vertically(self, image_path1, image_path2, num_page_1, num_page_2):
        # Charger les deux images
        img1 = Image.open(image_path1)
        img2 = Image.open(image_path2)

        # Créer une nouvelle image avec une hauteur égale à la somme des hauteurs des deux images
        # et une largeur égale à la largeur maximale des deux images
        new_image = Image.new('RGB', (max(img1.width, img2.width), img1.height + img2.height))

        # Coller les images dans la nouvelle image
        new_image.paste(img1, (0, 0))
        new_image.paste(img2, (0, img1.height))


        # Sauvegarder l'image résultante
        output_path=f"./temp/pages_{num_page_1}-{num_page_2}.jpg"
        new_image.save(output_path)
        
        return output_path

    def log_info(self, err):
        # Log the error to a file with timestamp and image path
        log_file = "error_log.txt"
        with open(log_file, "a", encoding="utf-8") as log:
            log.write(f"{datetime.now().isoformat()} | {err} |\n")        

    def describe_image(self, image_path, pages_numbers, use_history=True):
        """Envoie l'image à OpenAI avec l'historique si demandé"""
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if use_history and self.history:
            for entry in self.history[-3:]:  # On garde les 3 derniers échanges pour se rappeler de type de question PP/asso
                messages.append({"role": "user", "content": entry["user_input"]})
                messages.append({"role": "assistant", "content": entry["ai_response"]})
        
        # user_content = [
        #     {"type": "text", "text": "Extract the questions from this form"},
        #     {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
        # ]

        user_content = [
            {"type": "input_text", "text": "Extract the questions from this form"},
            {"type": "input_image", "image_url": f"data:image/jpeg;base64,{base64_image}"},
        ]        
        
        messages.append({"role": "user", "content": user_content})
        
        response = self.client.responses.create(
            # model="gpt-4o",
            model="o4-mini",
            #messages=messages,
            input=messages,
                reasoning={
                    "effort": "low"
                },
        )
        
        # description = response.choices[0].message.content
        description = response.output_text
        
        
        # try:
        #     extracted_questions=json.loads(description[description.find("["): description.find("]")+1])
        #     extraction='ok'
        # except Exception as e:
        #     print(e)
        #     extracted_questions=[]
        #     extraction='ko'

        # Sauvegarde dans l'historique
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "user_input": "Analyse de page de document",
            "ai_response": description,
            "page_image": image_path,
            # "extracted_questions": extracted_questions,
            # "extraction": extraction
        })

        # check valid json
        try:
            description=json.loads(description)
        except Exception as e:
            exc_type, exc_value, exc_tb = sys.exc_info()            
            self.log_info(f"{exc_value}\nLine: {exc_tb.tb_lineno}")
            return []
        
        if isinstance(description, list):
            for el in description:
                # el["page"]=image_path._str[image_path._str.find("page"):image_path._str.find(".jpg")]
                el["page"]=pages_numbers

            self.questions=self.questions+description
        elif isinstance(description, dict):
            # description["page"]=image_path._str[image_path._str.find("page"):image_path._str.find(".jpg")]
            description["page"]=pages_numbers
            self.questions.append(description)

        return description

    def save_history(self, output_folder, file_path="history.json"):
        """Sauvegarde l'historique dans un fichier JSON"""
        with open(output_folder/file_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def save_raw_questions(self, output_folder, file_path="extracted_raw_questions.json"):
        """Sauvegarde questions brutes dans un fichier JSON"""
        with open(output_folder/file_path, "w", encoding="utf-8") as f:
            json.dump(self.questions, f, ensure_ascii=False, indent=2)

    def save_cleaned_questions(self, output_folder, file_path="extracted_cleaned_questions.json"):        
        """Nettoyage & sauvegarde questions dans un fichier JSON"""
        deduplicated_questions_p1=deduplicate_raw_extracted_questions(self.questions)
        deduplicated_questions_p2=detect_duplicate_questions_v3(deduplicated_questions_p1)
        cleaned_questions=remove_duplicates_fuzz(deduplicated_questions_p2)
        with open(output_folder/file_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_questions, f, ensure_ascii=False, indent=2)


def print_progress_bar(total, progress):
    bar_length = 40
    filled_length = int(bar_length * progress // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f"\rProgress: |{bar}| {progress}/{total} pages", end='')
    sys.stdout.flush()


def main():
    
    describer = PDFDescriber()
    

    
    
    use_history = True
    # pdf_path=describer.docx_to_pdf("data/PU_P01_AAP07.docx")
    pdf_path=describer.docx_to_pdf("data/PU_P01_AAP07.docx")
    pdf_path=root_path/ pdf_path

    output_folder=root_path/"extracted_questions"
    output_folder.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(pdf_path)
    num_pages = len(reader.pages)
    for page_number in range(1, num_pages + 1):
    # for page_number in range(1, 7):
        try:
            print(f"Conversion de la page {page_number}/{num_pages}")



            

            if page_number==0:
                pages_numbers=[page_number, page_number+1]
            else:
                pages_numbers=[page_number-1, page_number]
            
            image_path = root_path/ describer.pdf_to_image(pdf_path, pages_numbers)

            print("Analyse en cours...")
            # image_path=root_path/"assembled_image.jpg"
            # description = describer.describe_image(image_path, use_history, pages_numbers)
            describer.describe_image(image_path=image_path, pages_numbers=pages_numbers, use_history=use_history)
            
            # print("\nRésultat:")
            # print(description)
            
            # Sauvegarde automatique de l'historique
            # describer.save_history()
            describer.save_raw_questions(output_folder=output_folder)
            
            
        except Exception as e:
            print(f"Erreur: {str(e)}")
        # finally:
        #     if 'image_path' in locals() and os.path.exists(image_path):
        #         os.remove(image_path)

        # print_progress_bar(num_pages, page_number)
        
    describer.save_cleaned_questions(output_folder=output_folder)

    
    os.remove(pdf_path)
       

if __name__ == "__main__":
    main()