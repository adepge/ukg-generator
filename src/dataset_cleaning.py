import json
import os
from tqdm import tqdm

def cleanUMLS(dataset_file: str, output_folder: str):
    """
    Cleans the UMLS dataset file.
    """

    # If the files do not exist, create them
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    acronym_file = output_folder + "/acronyms.json"   
    lemmas_file = output_folder + "/lemmas.json"
    term_filter_file = output_folder + "/term_filter.json"
    terms_file = output_folder + "/umls_terms.txt"

    # If the files exist, delete them
    if os.path.exists(acronym_file):
        os.remove(acronym_file)
    if os.path.exists(lemmas_file):
        os.remove(lemmas_file)

    # Initialize the dictionaries
    acronyms = dict[str, str]()
    lemmas = dict[str, str]()

    # Term types to filter out (reference: https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/release/abbreviations.html)
    term_filter = json.load(open(term_filter_file, "r"))

    abbreviation_filter = [
        "AA", "AB", "ACR", "CDA", "HS", "MTH_ACR", 
        "QAB", "QEV", "RAB", "SS"
    ]

    with open(dataset_file, "r") as f:

        grouped_terms = []
        grouped_acronyms = []
        current_concept = None
        preferred_term = None

        # First, count number of lines in file for progress bar total
        with open(dataset_file, "r") as f_count:
            num_lines = sum(1 for _ in f_count)

        f.seek(0)  # Reset file pointer to start

        for line in tqdm(f, total=num_lines, desc="Processing terms"):
            if not line: 
                continue

            """
            CUI: Unique identifier for the concept
            LAT: Language of term
            TS: Term status
            LUI: Unique identifier for the term
            STT: String type
            SUI: Unique identifier for string
            ISPREF: Atom status - preferred term for string within concept
            AUI: Unique identifier for the atom
            SAUI: Source asserted atom identifier (optional)
            SCUI: Source asserted concept identifier (optional)
            SDUI: Source asserted descriptor identifier (optional)
            SAB: Abbreviated source name (SAB)
            TTY: Abbreviation for term type in source vocabulary
            CODE: Most useful source asserted identifier (if multiple exist)
            STR: String
            SRL: Source restriction level 
            SUPPRESS: Suppressible flag
            """
            # Exclude CVF (last entry in line)
            CUI, LAT, TS, LUI, STT, SUI, ISPREF, AUI, SAUI, SCUI, SDUI, SAB, TTY, CODE, STR, SRL, SUPPRESS = line.split("|")[:-2]
            if SUPPRESS != "N":
                continue
            
            # Set the current concept if it is not set
            if not current_concept:
                current_concept = CUI

            # Process all terms for the current concept
            if current_concept != CUI:
                # Add the acronyms to the acronyms dictionary
                for acr in set(grouped_acronyms):
                    acronyms[acr] = preferred_term

                # Remove duplicates from the terms list
                grouped_terms = list(set(grouped_terms))

                # Add the lemmas to the lemmas dictionary
                for term, tty in grouped_terms:
                    lemmas[term] = (preferred_term, tty)

                current_concept = CUI
                preferred_term = None
                grouped_terms = []
                grouped_acronyms = []


            # Only process English terms (LAT == "ENG")
            if LAT == "ENG":
                if TS == "P" and STT == "PF" and ISPREF == "Y":
                    grouped_terms.append((STR, TTY))
                    preferred_term = STR
                else:
                    if TTY in abbreviation_filter:
                        grouped_acronyms.append(STR)
                    elif TTY in term_filter:
                        grouped_terms.append((STR, TTY))
                    else:
                        continue
    
    # Add the last concept to the dictionaries
    for acr in set(grouped_acronyms):
        acronyms[acr] = preferred_term

    # Remove duplicates from the terms list
    grouped_terms = list(set(grouped_terms))

    # Add the terms to the lemmas dictionary
    for term, tty in grouped_terms:
        lemmas[term] = (preferred_term, tty)

    # Write the dictionaries to the output files
    with open(acronym_file, "w+") as f:
        json.dump(acronyms, f, indent=4)
    with open(lemmas_file, "w+") as f:
        json.dump(lemmas, f, indent=4)
    
    with open(terms_file, "w+") as f:
        for term in lemmas.keys():
            f.write(f"{term}\n")


def cleanCADRO(dataset_file: str, output_file: str):
    """
    Cleans the CADRO dataset file.
    """
    cadro_data = json.load(open(dataset_file, "r"))
    terms = []
    for category in cadro_data["categories"].values():
        terms.append(category["title"])
        for subcategory in category["subcategories"].values():
            terms.append(subcategory["title"])
            if "terms" in subcategory:
                for term in subcategory["terms"]:
                    terms.append(term)

    terms = list(set(terms))
    terms.sort()
    
    with open(output_file, "w+") as f:
        for term in terms:
            f.write(f"{term}\n")

def cleanSNOWMED(dataset_file: str, output_file: str):
    """
    Cleans the SNOWMED dataset file.
    """
    
    with open(dataset_file, "r") as f: 
    
        terms = []

        # First, count number of lines in file for progress bar total
        with open(dataset_file, "r") as f_count:
            num_lines = sum(1 for _ in f_count)

        f.seek(0)  # Reset file pointer to start

        for line in tqdm(f, total=num_lines, desc="Processing terms"):
            if not line: 
                continue
            # Skip the first line (header)
            if line.startswith("id"):
                continue

            id, effective_time, active, module_id, concept_id, language_code, type_id, term, case_sig_id = line.strip().split("\t")

            if term.startswith("["):
                continue
            if term.startswith("\"") or term.startswith("'"):
                continue
            if term.startswith("©"):
                continue
            if len(term) < 3:
                continue
            terms.append(term)

    terms = list(set(terms))
    terms.sort()

    with open(output_file, "w+") as f:
        for term in terms:
            f.write(f"{term}\n")

if __name__ == "__main__":
    clean = "snowmed"
    if clean == "umls":
        dataset_file = "/home/adamg/Documents/Repositories/ukg-generator/datasets/UMLS/MRCONSO.RRF"
        output_folder = "/home/adamg/Documents/Repositories/ukg-generator/resources/ontology/umls"
        cleanUMLS(dataset_file, output_folder)
        print("UMLS dataset cleaned successfully")
    elif clean == "cadro":
        dataset_file = "/home/adamg/Documents/Repositories/ukg-generator/datasets/CADRO/ontology.json"
        output_file = "/home/adamg/Documents/Repositories/ukg-generator/resources/ontology/cadro/terms.txt"
        cleanCADRO(dataset_file, output_file)
        print("CADRO dataset cleaned successfully")
    elif clean == "snowmed":
        dataset_file = "/home/adamg/Documents/Repositories/ukg-generator/datasets/SNOWMEDCT/Full/Terminology/sct2_Description_Full-en_INT_20260101.txt"
        output_file = "/home/adamg/Documents/Repositories/ukg-generator/resources/ontology/snowmedct/terms.txt"
        cleanSNOWMED(dataset_file, output_file)
        print("SNOWMEDCT dataset cleaned successfully")