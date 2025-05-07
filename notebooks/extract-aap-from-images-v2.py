import os
import base64
import json
from pdf2image import convert_from_path
from openai import OpenAI
from datetime import datetime
import dotenv

dotenv.load_dotenv("./streamlit_local/.env")

class PDFDescriber:
    def __init__(self):
        self.client = OpenAI()
        self.history = []
        self.system_prompt="""
            I have a collection of form images that include questions in different configurations. The forms may include:

            Straight and direct interrogative questions:
            Examples:
            "Where is the project located?"
            "Who are the target beneficiaries?"

            Informational expectations presented in a descriptive (non-interrogative) style:
            Examples:
            "Project description"
            "Expected outcomes"

            Questions that include an explanation, sub-questions, or multiple choice items as guidance:
            Examples:

            Example 1: Project Justification and Beneficiary
            "Problem Analysis (max. 600 words)
            Please provide:
            A description of the current situation or issue related to the project (background, geographic region, and beneficiaries, etc).
            an analysis of the problem the project is trying to address. Develop a Problem Tree by defining ..."
            
            Example 2: Date of Submission
            "When will the project be submitted to the donor?
            Is the submission date aligned with the donor’s deadlines?
            Are there any internal deadlines for reviews before submission?
            Would a timeline graphic of submission milestones be helpful?"

            Example 3: Blue Planet Fund outcomes
            "Which Blue Planet Fund outcome(s) does your project address? Select all that apply.
            □ Marine Protected Areas (MPAs) and Other Effective Conservation Measures (OECMs)
            □ Illegal, Unreported, and Unregulated Fishing (IUU)
            □ International and large-scale fisheries
            □ None of the above."

            The questions may be segmented by sections, concerning the applicant organization or the project to be financed
            **Very important**: provide the information "organization" or "project" in either case

            Your task is to process the provided images of these forms, extract all the questions (regardless of their configuration), and output a JSON-like list of items. 
            Each item in the list should represent one question or one key informational prompt extracted from the image, and the theme (organization or project).

            The expected output format should be like this:
            [
                {"question": "Question 1 extracted from the image + multiple choice options +  relevant information notes", "section": "organization"},
                {"question": "Question 2 extracted from the image + multiple choice options +  relevant information notes", "section": "project"},
                {"question": "Question 3 extracted from the image + multiple choice options +  relevant information notes" "section": "project"}
                ...
            ]

            Make sure to:
            Accurately extract and capture the essence of the question or informational prompt from every form, even if the wording is not in a strictly interrogative style.            
            Include  multiple choice items, sub-questions or any guidance details if they are integral to the overall question prompt.
            Always provide the section the questions refer to, which can be "organization" or "project"
            Preserve the order of appearance as found in the images (if applicable) or indicate if the order is arbitrary.

        """
       

    def pdf_to_image(self, pdf_path, page_number, output_folder="temp"):
        """Convertit une page PDF en image"""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        images = convert_from_path(pdf_path, first_page=page_number, last_page=page_number)
        if not images:
            raise ValueError(f"Aucune image trouvée pour la page {page_number}")
        
        image_path = os.path.join(output_folder, f"page_{page_number}.jpg")
        images[0].save(image_path, "JPEG")
        return image_path

    def describe_image(self, image_path, use_history=True):
        """Envoie l'image à OpenAI avec l'historique si demandé"""
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if use_history and self.history:
            for entry in self.history[-3:]:  # On garde les 3 derniers échanges pour se rappeler de type de question PP/asso
                messages.append({"role": "user", "content": entry["user_input"]})
                messages.append({"role": "assistant", "content": entry["ai_response"]})
        
        user_content = [
            {"type": "text", "text": "Extract the questions from this form"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
        
        messages.append({"role": "user", "content": user_content})
        
        response = self.client.chat.completions.create(
            # model="gpt-4o",
            model="o4-mini",
            messages=messages,
            # temperature=0
        )
        
        description = response.choices[0].message.content
        
        # Sauvegarde dans l'historique
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "user_input": "Analyse de page de document",
            "ai_response": description,
            "page_image": image_path
        })
        
        return description

    def save_history(self, file_path="history.json"):
        """Sauvegarde l'historique dans un fichier JSON"""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)


def main():
    
    describer = PDFDescriber()
    

    
    pdf_path = "./data/PU_P01_AAP07.pdf"            
    use_history = "o"
    
    for page_number in range(3, 6):
        try:
            print("Conversion de la page...")
            image_path = describer.pdf_to_image(pdf_path, page_number)
            
            print("Analyse en cours...")
            description = describer.describe_image(image_path, use_history)
            
            print("\nRésultat:")
            print(description)
            
            # Sauvegarde automatique de l'historique
            describer.save_history()
            
        except Exception as e:
            print(f"Erreur: {str(e)}")
        finally:
            if 'image_path' in locals() and os.path.exists(image_path):
                os.remove(image_path)
       

if __name__ == "__main__":
    main()