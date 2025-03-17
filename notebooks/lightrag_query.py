# query
import os
import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, gpt_4o_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.utils import setup_logger
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from itertools import product
import pandas as pd
from langchain_openai import ChatOpenAI
from time import time as timing


os.environ["OPENAI_API_KEY"] = "key"

setup_logger("lightrag", level="INFO")


rag = LightRAG(
    working_dir="./data/lightrag_db",
    embedding_func=openai_embed,
    llm_model_func=gpt_4o_mini_complete,
    vector_storage="FaissVectorDBStorage",
    vector_db_storage_cls_kwargs={
        "cosine_better_than_threshold": 0.3  # Your desired threshold
    }        
)

# rag.initialize_storages()
# initialize_pipeline_status()


# Perform naive search
# mode="naive"
# Perform local search
# mode="local"
# Perform global search
# mode="global"
# Perform hybrid search
# mode="hybrid"
# Mix mode Integrates knowledge graph and vector retrieval.
# mode="mix"





#=======setup llm evaluator===========
llm_evaluator = ChatOpenAI(model_name="gpt-4o", temperature=0.2,)

# Eval ran reply with llm
def score_reference_vs_rag_with_gpt(question, reference_text, ragReply, llm=llm_evaluator):

    prompt=f"""
        Evaluate the quality of a Retrieval-Augmented Generation (RAG) answer by comparing it against a reference text for a given question.  

        ### Inputs:  
        - **Question:** {question}  
        - **Reference Text:** {reference_text}  
        - **RAG Answer:** {ragReply}  

        ### Evaluation Criteria:  
        Rate the RAG answer on a scale of **1 to 10** based on the following aspects:  
        1. **Coherence:** How logically structured and consistent the answer is.  
        2. **Coverage:** How well the answer addresses key points found in the reference text.  
        3. **Clarity:** How clearly the answer conveys information.  

        **Important Consideration:**  
        - If the RAG answer explicitly states that it lacks sufficient information to fully answer the question, do **not** penalize it.  

        ### Output Format:  
        Respond **only** with a single number between **1 and 10** (e.g., 1, 2, ..., 10).  

    """

    resp=llm.invoke(prompt)    
    
    
    try:
        return int(resp.content)
    except:
        return resp.content

# ====================================






#=======setup llm rewriter============

system="""
    You are a question rewriter tasked with improving input questions to optimize them for vector store retrieval. 
    Your mission is to refine, rephrase, and enhance the provided questions to ensure they are:
    * Clear and easy to understand.
    * Concise and focused.
    * Optimized for effective retrieval by removing ambiguities, unnecessary words, and redundancies.
    * Written in an interrogative form while preserving the original intent.

    #### Input Fields to Rework:
    * Project Description: Reword questions that focus on the project’s overall scope and objectives.
    * Country and City: Refine questions to specifically inquire about the project’s location.
    * Target Beneficiaries: Enhance questions to clarify the population or group that benefits from the project.
    * Number of People Concerned: Rework questions to quantify how many people the project impacts.
    * Context, Environment, Project Rationale, and Challenges: Rephrase questions that ask for background information, challenges, and the reasoning behind the project.
    * Project Start Date / End Date: Rework questions regarding the project’s timeline.
    * Financial Information:
        * Project Budget: Reword questions about the overall project budget.
        * Total Project Cost: Rephrase inquiries about the total cost of the project.
        * Donation Request Amount: Refine questions asking about the amount of funding requested.
        * Provisional Project Budget: Rework questions about the detailed provisional budget for the project.
        * Current Year Budget: Enhance questions related to the budget specific to the current year.


    #### Response Format:
    For each input question, rephrase it in a clear, concise, and interrogative form, optimized for vector store retrieval. Return only the reworked question.
"""

re_write_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        (
            "human",
            "Here is the initial question: \n\n {question} \n Formulate an improved question.",
        ),
    ]
)
llm_rewriter = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.2)
question_rewriter = re_write_prompt | llm_rewriter | StrOutputParser()

#======================================





#================ list of questions ================
# La 'reference_answer' est copiée manuellement du document pour être utilisée comme texte de référence lors de l'évaluation

questions=[
    {
        "q_#": 1,
        "question": "Description of the project", 
        "reference_answer": """    
            Brief project description
            East Kalimantan Province in 2021/2022 received great attention nationally
            because of the moving of the state capital city (Jakarta) to a location near
            the city of Balikpapan and Penajam Paser Utara in East Kalimantan Province.
            The development of the new capital will start in 2022. Although the
            Indonesia President commit to develop the new capital as Forest and Smart
            City, the surrounding area particularly the coastal area such as Delta
            Mahakam and Adang Bay might get high pressure as the consequence of the
            new development and the movement of 1.5 million people to the new
            capital.
            Delta Mahakam, in the eastern part of East Kalimantan, is an area that is
            relatively close to the prospective center of the State capital (about 100 km).
            Mahakam Delta is naturally a mangrove habitat, but due to excessive land
            clearing for extensive aquaculture about 47.5 % of the mangrove ecosystem
            is degraded to be converted into aquaculture (2017). Despite various
            conservation efforts by different parties and the government, land clearing
            still continues. Delta Mahakam land ownership is government land that has
            designated as a production forest, but this area has been inhabited by
            residents from generation to generation.
            Adang Bay is one of the coastal villages in Adang Bay, Paser Regency, on the
            southern part of East Kalimantan Province (about 100 km from the new
            capital). This area is also experiencing land conversion to increase
            aquaculture, besides there are several locations in coastal areas that are
            affected by abrasion. Restoration activities in East Kalimantan Province are
            needed to restore a degraded environment, as well as to support the vision
            of the nation's capital as a green city.
            The ecosystem in Delta Mahakam and Adang Bay 1 are also home to
            critically endangered species, such as the nasal monkey (proboscis
            monkey), endemic to the island of Borneo. On a global scale, the mangrove
            is a key ecosystem to answer the challenge of carbon sequestration and
            fight against climate change.
            The objective of the project is therefore to contribute to restore the
            degraded mangrove forest in East Kalimantan (Delta Mahakam and Adang
            Bay) as home of endemic and endangered species including proboscis
            monkey and key ecosystem to mitigate and to adapt the impact of climate
            change; and this, through four main actions: raising awareness of the
            stakeholders, rehabilitating degraded mangrove forest, supporting the
        """
    },
    {
        "q_#": 2,
        "question": "Country and city", 
        "reference_answer": """
            The location of the project is in Paser District (Adang Bay village) and Kutai
            Kartanegara district (Delta Mahakam) East Kalimantan Province. The location
            of project is nearby the new capital of Indonesia which is in the Penajam
            Paser Utara (around 130-160 km)
        """
    },
    {
        "q_#": 3,
        "question": "Target beneficiaries", 
        "reference_answer": """
            Number of direct beneficiaries of the pilot project: 3245 people with the
            proportion of 30% women and 70% men.
            Number of indirect beneficiaries: 3000 people by assuming at least the
            project will give benefit indirectly to 1500 people per location including in
            East Kalimantan and Indonesia.
            The target groups include:
            - School children (primary schools and secondary schools)
            - Teachers (primary school teachers)
            - Community members (villagers, consists of fish farmers, women group,
            and youth)
            - Village officials
            - Stakeholders from various institutions (government institutions,
            universities, and non-government organizations)
            - Public audience in general (reached by Media)
            Other potential groups:
            - High school and university students
            - Environmental activists 
        """
    },
    {
        "q_#": 4,
        "question": "Number of people concerned", 
        "reference_answer":"""
            Number of direct beneficiaries of the pilot project: 3245 people with the
            proportion of 30% women and 70% men.
            Number of indirect beneficiaries: 3000 people by assuming at least the
            project will give benefit indirectly to 1500 people per location including in
            East Kalimantan and Indonesia.
        """ 
    },
    {
        "q_#": 5,
        "question": "Context, environment, project rationale and challenges", 
        "reference_answer": """
            Context & environment and development challenges
            Geographic and socio-economic context
            East Kalimantan is one of the richest provinces in Indonesia and the main
            contribution to the national GDP. Before palm oil and mining coal booming in
            early 2000, forestry, mining and gas sectors are the backbone of economic
            development in East Kalimantan. Because too much depending on the
            unrenewable natural resources, the economic growth of East Kalimantan
            gradually declines and, in 2016, reached the minus point because of the
            lowest price of coal at the global level. In 2019, Indonesia government has
            decided to move the capital of Indonesia from Jakarta to East Kalimantan.
            Currently, the government accelerate the infrastructure development of new
            capital.

            The project will be implemented in several regions of Mahakam Delta and
            Adang Bay. Mahakam Delta is located on the eastern coast of the island of
            Borneo, in East Kalimantan province, which is one of the five provinces that
            has the lowest population density in Indonesia. This province is also the main
            contributor to the national GDP, mainly for its wealth in oil and gas. It is
            nevertheless aquaculture activities which constitute the main source of
            income for the local population. About 90% of the population depend on it
            for their livelihood. As a result, 54.19% of the Mahakam Delta has been
            converted to shrimp ponds. The majority of exports from the area are made
            up of tiger shrimp and white shrimp that are farmed in the delta ponds and
            along the Paser District's shore.

            Paser District is located on the east coast of East Kalimantan Province. The
            village of Adang Bay is located in the coastal area of this district, in Adang
            Bay. This area is a conservation area managed by the Ministry of Forestry
            (KPHP). Therefore, limited economic activities are allowed in this area.
            However, since the late 1990s, massive clearing for the construction of
            aquaculture ponds has destroyed the mangrove forest in the area. According    
            to the District Pastor's Investment Agency, about 1,506 people live in Adang
            Bay. Most of them work as fishermen, fish farmers and swallowers. The
            village government and the community have made a strong commitment to
            conserve the area by adhering to the jurisdictional REDD+ approach, funded
            by the World Bank's FCPF or Forest Carbon Partnership Facility Project.
            Environmental context
            Largest archipelago in the world (more than 13,000 islands), Indonesia has
            an area of 1,905,000 km2 of which less than 50% is still covered by forests
            today, while the country is part of the 3rd largest planetary tropical
            forest zone (after the Amazon and the Congo Basin). More than half of
            Indonesian forests have disappeared since 1960. However, they are home to
            a large part of the world's biodiversity (more than 10% respectively of plant,
            mammal, reptile and bird species). Today, the country counts for 3 to 5% of
            annual global greenhouse gas emissions (among the 10 most emitting
            countries) including more than 50% due to land use, their change of land use
            and the exploitation of forests.
            Indonesia is home to almost 1/4 of the world's mangroves (20%). This
            maritime ecosystem, made up of a set of mainly woody plants (the most
            notable species being the mangrove), develops in the swinging area of the
            tides of the low coasts and in marshes at the mouth of certain rivers. Of the
            nearly 3.2 million hectares of mangrove forest 2 in the country today, more
            than 50,000 ha are lost each year.
            The mangrove is one of the most productive ecosystems on the planet,
            home to a particularly abundant biomass. The mangroves' root system is
            notably a biotope where a variety of fish and crabs live and reproduce. The
            mangrove thus provides important resources (forestry and fishery) to coastal
            populations, a natural “buffer” zone adapted to salinity, filtering sediment
            and pollution carried by rivers and the sea, and preserving the fresh water
            resources of the land. They are a food security and livelihood issue, in
            particular providing income to fishing communities. This ecosystem is also
            an important natural fount of carbon, with Indonesian mangroves storing
            around 5 times more carbon per hectare than terrestrial forests. The
            government of Indonesia has taken into account this ecosystem in its REDD+
            strategy, implemented in the only pilot province of East-Kalimantan, with the
            Provincial Council on Climate Change (DDPI) with the support of the World
            Bank in the framework of the “Forest Carbon Partnership Facility Project”.
            Finally, the mangrove plays a key role in natural defense. The complex
            network of mangrove roots can help reduce wave power, which limits erosion
            and protects coastal communities from the destructive forces of tropical
            storms. Mangroves provide protection against extreme weather events and
            tsunamis, and can adapt to rising sea levels and subsidence. They therefore    
            contribute to reducing the risk of disasters, to the resilience of communities
            and ecosystems and to their adaptation to climate change.
            In Mahakam Delta, results from a study conducted in 2018 and 2019 by the
            Kutai Kartanegara District has shown that 47.8% of mangrove forests are
            deteriorated.
            Table 1. Critical Criteria of Mahakam Delta Mangrove3
            Critical Criteria Land Area (ha) Percentage
            Damaged 7,034 5.6
            Severe 52,945 42.2
            Undamaged 65,522 52.2
            Total 125,502 100.0
            
            Source: The Result of Spatial Analysis of Mangrove Damage Level (2018)

            With the plan to move the state capital to Penajam Paser Utara District
            (PPU), the development activities to create this new big city will take place
            massively. The central government has planned to create a green city for the
            new capital, which construction will start in 2022, but various problems still
            pose challenges in locations outside the new capital. On the one hand, a
            close government center can control the surrounding environment to keep it
            conserved, but the gap in the quality of human resources and plans to move
            a large number of people from Jakarta to this area will certainly cause
            pressure on the environment.

            Biodiversity issues
            The mangrove of Mahakam Delta conceals a rich marine and arboreal
            biodiversity, characterized by a large variety of fish, arthropods, reptiles
            such as the marine crocodile (Crocodylus porosus), aquatic mammals such
            as the Irrawaddy dolphin (Orcaella brevirostris) or terrestrial like the nasal
            monkey (Nasalis larvatus), these last 2 species being considered as being
            “endangered” by the IUCN.
            The deforestation of Mahakam Delta’s mangrove hampers the effort to
            conserve this type of species, for example by fragmenting the habitat of the
            nasal monkey, whose interaction between populations strongly depends on
            the continuity of the canopy. The isolation of these populations makes them
            more vulnerable to poaching. The long-nosed monkey, endemic of Borneo
            Island is listed as “Endangered” by the IUCN as it has undergone extensive    
            population reductions across its range, and ongoing hunting and habitat
            destruction continue to threaten most populations. Numbers have
            declined by more than 50% (but probably less than 80%) over the past 3
            generations (approximately 36-40 years).4 At the scale of Mahakam Delta,
            only 2 censuses have been conducted to monitor this specie, respectively in
            1997 and 2005 which reflects the lack of resources of local institutions to
            conserve and protect this biodiversity.
            In addition, the degradation of this ecosystem leads to a decrease in fish
            stocks in the delta, threatening both fishermen and species such as sea
            crocodiles and dolphins. The situation is currently might threatening to
            exacerbate human-animal conflicts and therefore to further decrease the
            populations of the above-mentioned species, even threatening them with
            extinction. Hence, beside preventing the mangrove forest conversion into
            palm oil plantation, aquaculture ponds, and other usages, the reforestation
            activity is necessary to improve the degraded mangrove ecosystem in the
            coastal area.
            Paradoxically, the considerable modification of delta habitats resulted in a
            very substantial increase in populations of birds associated with open
            wet areas, such as egrets (100 individuals in 1987 to nearly 15,000
            individuals in 2013). Likewise, some species of heron have seen their
            population sizes increase considerably, such as the purple heron or the Javan
            pond-heron, the lesser adjutant, ducks, Sunda teal and the wandering
            whistling-duck also seem to have used the habitats created by the clearings
            to considerably increase their populations.
            The populations of these species have benefited of new feeding areas when
            the shrimp ponds were developed. Indeed, egrets, ducks, and waders use
            the shrimp ponds in high numbers on cyclical basis when shrimp ponds are
            emptied for shrimp harvesting. The presence of pristine areas, with large
            trees or dense copses of smaller species (Nypa) removed from human
            presence, is also favourable for the reproduction of these species. Here they
            find quiet conditions for reproduction or gatherings (dormitories). Amongst
            the species observed in 2013 and those not observed in 1987, eight dwell in
            an aquatic environment and directly depend on the shrimp ponds: darter,
            stilts, grey heron, black-crowned night heron, intermediate egret, western
            marsh-harrier and the Garganey. The opening of shrimp ponds was the
            obvious factor leading to the growth of all these bird populations.
            
            Institutional Context
            The key players in coastal region in East Kalimantan including in Delta
            Mahakam Ulu (Delta Mahakam) and Delta Mahakam (Adang Bay) are
            relatively similar. Since the area located or nearby the conservation area and
            forest production area, the Ministry of Forestry via Nature Conservancy
            Agency in East Kalimantan and Forest Management Unit (provincial
            government agency) are the most influence actor. They have authority to
            determine the activities which allowed and not allowed in the area. However,
            they cannot control the vast area of conservation area since 50 percent of
            mangrove forest in the region have been degraded. Besides government, the
            others key actors are fishermen, fish farmers, swallow workers and investors
            in aquaculture sectors. Those actors have shaped the landscape of coastal
            area in Delta Mahakam and Adang Bay over the past 20 years. In their hand
            the future of sustainable aquaculture is determined. Environmental and
            development NGOs, oil and gas company and other parties has programme
            in their area. Most of the programme focus on improving the livelihood of the
            local people and restoring the mangrove forest.
            
            The Movement of Indonesian New Capital
            Paser District (East Kalimantan Province) will soon be the site of Indonesia's
            new political capital, Nusantara, as part of the plan to move the country's
            capital from the island of Java to the island of Borneo, which is home to one
            of the world’s largest rainforests.
            Jakarta, the current political capital which will become the country's
            economic capital by 2045, is currently facing several environmental, climatic
            and demographic problems and challenges: overpopulation, heavy pollution,
            rising water levels, frequent flooding, etc. In order to deal with the inevitable
            future security issue, the Indonesian government has decided to build a new
            capital 2,000 km away from Jakarta, in the province of East Kalimantan,
            more precisely between the towns of Balikpapan and Samarinda. With the
            legislation for the relocation of the new capital published, the physical
            development of the new capital will begin in 2022. In August 2024, the
            President plans to celebrate Indonesia's Independence Day in the new
            capital.
            The government plans to make the new capital a "forest city" by strongly
            preserving forest areas and using sustainable energy. However, many argue
            that the development of the new capital could lead to environmental
            degradation and loss of essential biodiversity, especially in the mangrove
            forest. The majority of the Indonesian population, including the local
            population, supports the new capital movement by echoing the effect of
            equitable development. Indeed, for decades, the natural resources of
            Kalimantan Island have been exploited to support Indonesian development,
            especially that of Java Island.
            The location of the project (Delta Mahakam and Adang Bay -Adang Bay) is an
            area relatively close to the potential centre of the state capital (about 100-
            200 km).

            Environment and development challenges
            a) Aquaculture industry
            Mahakam Delta area is under pressure from both the industrial and
            agricultural sectors, including aquaculture facing a national high dynamic.
            From 2015 to 2035 it is expected a destruction of 600,000 ha of mangrove
            for shrimp farm at the national scale. The World Bank (2013) estimates a
            pressure to double cultivated shrimp production from currently 300,000 t
            (produced by 600,000 ha of ponds) to 600,000 t/1,000,000 t by 2030 to fulfil
            the demand. However, with improvements in brackish water aquaculture
            productivity, halting palm oil concession to use mangroves, along with
            maintaining other mangrove use pressures at moderate levels, the net loss
            of mangroves in the next two decades could be reduced to around 23,000 ha
            at this same scale.
            The East-Kalimantan Province is the new area to develop aquaculture ponds
            as Java, Sumatra and Sulawesi islands are facing a decrease of the
            production and the destruction of their environment due to unsustainable
            practices.
            Feature 1: Forecasted mangrove loss at six mangrove regions in Indonesia
            in the next two decades due to land use change under pessimistic scenario.
            Circle size indicates potential loss areas in Sumatra, Kalimantan, and Papua;
            as for Java, Sulawesi and Maluku potential loss areas are represented by the
            smaller circles.
            Scientific studies also show that the percentage of mangrove natural
            recovery is higher in East-Kalimantan with 1.4%/year against 0.7%/year in
            other islands in inactive ponds. This suggests to consider conservation
            activities in specific areas of Mahakam Delta. At the scale of Mahakam Delta,
            the table below for which the percentage (43.7%) is as higher as the
            remaining mangrove forest (48.5%) highlights the dominance of aquaculture.

            
            b) Demography
            The demographic issue must also be considered. Indeed, the announcement
            in 2019 of the relocation of the political and administrative capital of Jakarta
            to the province of East Kalimantan, between the cities of Balikpapan and
            Samarinda, suggests strong migrations, the development of infrastructures
            but also a growing demand for aquaculture products. By 2024, the
            Indonesian Minister of Planning hopes to transfer nearly 1.5 million public
            officials and political representatives in East Kalimantan.
            Delta Mahakam Ulu village, which belongs to Delta Mahakam district, is
            located in the northern part of the Mahakam Delta. The location of Delta
            Mahakam sub-district is close to the state-owned oil company (Pertamina),
            formerly VICO. Due to the proximity of a fairly large company, the
            community's economy is quite dynamic and the area offers a variety of jobs.
            However, the number of people who still carry out the traditional work of
            fishermen and fish farmers is still quite high, especially in the coastal areas.
            Working as a fish farmer has become one of the choices of the community as
            land is available for opening ponds. The conversion of mangrove forests into
            ponds has been going on for decades, but the production of fish and shrimp
            has decreased from time to time. Based on various studies and research,
            planting a number of mangroves in ponds can improve the soil and water
            quality in the ponds so that they can provide sustainable production. The
            farmer groups in Delta Mahakam Ulu ponds are beginning to realise the
            importance of planting mangroves in the ponds, and therefore need support
            from various parties.
            c) Other issues
            The table below represents a summary of estimation of potential loss and
            gain of mangroves in six major regions by 2035. The Kalimantan Island is the
            one to analyze in order to justify Planète Urgence and partners’ information.
            The analysis does not yet consider the movement of new capital issue which
            very likely affect the mangrove forest in East Kalimantan as well.
            
            This table highlight the multiple and complex context in which mangrove loss
            depends and confirms challenges faced in Mahakam Delta area. The lack of
            resources (financial, human resources, material) of local authorities coupled
            with a lack of transparency, coordination and communication around
            responsibilities of each actors impacts the management of mangrove forests,
            natural resources and territorial development.    
            
            Another issue that has also had a major impact on life in Indonesia, including
            East Kalimantan, is the Covid 19 global pandemic that has attacked the
            entire world since early 2020. The Covid 19 pandemic has had a major
            impact on life in Indonesia. East Kalimantan is a province outside Java Island
            with the highest rate of exposure to Covid, which has resulted in the
            government imposing a lockdown and restrictions on community activities.
            At the beginning of 2022, community activities began to return to normal,
            but a new variant emerged, namely Omicron, which spread very quickly.
            Facing a pandemic situation that has not ended, of course, the project must
            continue but still pay attention to security, safety, and practice health
            protocols.
            
            3. Strategy & theory of change
            The three years project aims to contribute to restore the degraded of
            mangrove ecosystem in Production Forest (Mahakamm Delta) and
            Conservation area (Adang Bay). In doing so, the project will address the key
            problems in those regions:
            a. Lack of awareness of local people on mangrove ecosystem,
            biodiversity issue and waste
            b. Huge area of degraded mangrove forest which affect the resilience of
            local people in facing climate change, the habitat of endangered
            species and local economy;
            c. Lack of alternative sustainable livelihood in coastal area;
            d. Poor governance particularly on mangrove ecosystem and its
            environmental and economy issue.
            To overcome those problems, Planet Urgence and its partners will work by
            implementing the PU FORET strategy which rely on three components:
            1. Restore degraded forest;
            2. Environmental awareness;
            3. Strengthening livelihood of local people.
            In addition, the involvement of local NGOs, local community and volunteer is
            key for the successful of the project and the sustainability the impact of the
            project. Therefore, PU will reinforce the capacity of those local stakeholders
            to ensure they can carry out the project activities and together achieve the
            long-term goal of the project.    
            """
    },
    {
        "q_#": 6,
        "question": "Project start date / end date", 
        "reference_answer": "March 2023 – February 2026"
    },
    {
        "q_#": 7,
        "question": """Project budget 
            Total amount of the project (in Euros) 
            
            Amount of donation requested from the Foundation (in Euros) 
            
            Detailed provisional project budget 
            
            Detailed project budget for current year
        """, 
        "reference_answer": "The total required resources is 818 341 € for the period 2023-2026"
    },                

]
 
# ===========================



#=============== boucle Q/A/evals===================
modes=["naive", "local", "global", "hybrid", "mix"]
q_a_list=[]
for mode, question_args in list(product(modes, questions)):
    question=question_args["question"]

    enhanced_question= question_rewriter.invoke({"question": question})
    print(f"---Question: {enhanced_question}\n")
    print(f"---Search mode: {mode}\n")

    t=timing()
    resp=rag.query(
        enhanced_question,
        param=QueryParam(mode=mode)
    )
    tf=timing()-t
              

    eval_score=score_reference_vs_rag_with_gpt(enhanced_question, question_args["reference_answer"], resp)

    
    print(f"""Eval_score: {eval_score}""")

    print("\n-------")

    q_a_list.append(
        {"enhanced_question": enhanced_question, "answer": resp, "mode": mode, "eval_score_llm": eval_score, "exec_time": tf}
    )

pd.DataFrame(q_a_list).to_csv("./rag-mahakam-lightrag.csv", index=False)