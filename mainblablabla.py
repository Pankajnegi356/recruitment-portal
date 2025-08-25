from sentence_transformers import SentenceTransformer, util
from pprint import pprint
from resume_json_to_txt import generic_json_to_text,extract_clean_json
from llama_resumer import create_profile_summary
from typing import List, Dict
from jd_skillextractor import extract_skills_from_jd
import resume_extractor
from resume_extractor import fetch_resume_url_from_inbox,process_resume_from_url
from jd_extr import extract_jd_details,extract_jd_details_from_folder
from skill_matcher import process_resumes
from schedule_test import schedule_assessments_from_output
from db_update_candidates import update_candidates_from_skill_matching
 
if __name__ == "__main__":
    resume_jsons = []
    resume_urls = fetch_resume_url_from_inbox()
    if not resume_urls:
        print("⚠️ No resumes to process.")
    else:
        for url in resume_urls:
            resume=process_resume_from_url(url)
            print(resume)
            print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
            resume_jsons.append(resume)
    print(resume_jsons)
    path="/home/azureuser/agentic_hr/JD"
    job_description_text= extract_jd_details_from_folder(path)
    output = process_resumes(resume_jsons, job_description_text)
    print(output)
    pprint(output)

#     [{'Email': 'suman.nanhe@gmail.com',
#   'JD_Skills': ['Azure Data Factory',
#                 'SQL',
#                 'ETL development',
#                 'Data pipeline implementation',
#                 'Data quality assurance',
#                 'Pipeline optimization',
#                 'Troubleshooting',
#                 'Documentation',
#                 'Cloud storage',
#                 'APIs',
#                 'Data governance',
#                 'Compliance',
#                 'DevOps',
#                 'Batch and incremental loads'],
#   'Name': 'Suman Parashari',
#   'Phone': '+91-9654603260',
#   'Score': 0.3804,
#   'Summary': 'Professional in Computer Science. Results-driven Quality '
#              'Assurance (QA) expert with over 8 years of experience in '
#              'ensuring seamless delivery of software products across various '
#              "domains. Holding a Master's degree in Computer Applications from "
#              "Uttar Pradesh Technical University and a Bachelor's degree in "
#              'Mathematics and Computer Science from Allahabad University. '
#              'Proficient in Automation Testing using Selenium WebDriver, API '
#              'and Manual testing, Cross-browser compatibility testing, '
#              'Webservice testing using Postman, and experienced in delivering '
#              'daily status reports and weekly reports. Skilled in implementing '
#              'Automation Frameworks including Data Driven and Page Objects '
#              'models. Proven track record of successfully leading projects '
#              'such as Neogov, Ovunet, JSHealth Vitamins, and Zaapi, with '
#              'expertise in executing regression tests, smoke testing, sanity '
#              'testing, creating test plans, logging issues, and re-testing '
#              "JIRA tickets. Holding a Master's degree in Technology from Abdul "
#              'Kalam Technical University, adding to the technical expertise. '
#              'Skills: Automation Testing using Selenium WebDriver, API and '
#              'Manual testing, Cross-browser compatibility testing, Webservice '
#              'testing using Postman, Delivery of daily status reports and '
#              'weekly reports, Automation Frameworks implemented Data Driven, '
#              'Page Objects model etc. Skills & Tools: Automation Testing using '
#              'Selenium WebDriver, API and Manual testing, Cross-browser '
#              'compatibility testing, Webservice testing using Postman, '
#              'Delivery of daily status reports and weekly reports, Automation '
#              'Frameworks implemented Data Driven, Page Objects model etc.'}]

    # Update Candidates in Mysql DB   
    update_candidates_from_skill_matching(output, threshold=0.3)

    # Schedule assessments for all candidates
    schedule_assessments_from_output(output)
