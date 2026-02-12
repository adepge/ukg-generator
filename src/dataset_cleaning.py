import json
import os

def cleanUMLS(dataset_file: str, output_folder: str):
    """
    Cleans the UMLS dataset file.
    """

    # If the files do not exist, create them
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    acronym_file = output_folder + "/acronyms.json"   
    term_file = output_folder + "/terms.json"
    lemmas_file = output_folder + "/lemmas.json"

    # If the files exist, delete them
    if os.path.exists(acronym_file):
        os.remove(acronym_file)
    if os.path.exists(term_file):
        os.remove(term_file)
    if os.path.exists(lemmas_file):
        os.remove(lemmas_file)

    # Initialize the dictionaries
    acronyms = dict[str, str]()
    lemmas = dict[str, str]()
    terms = dict[str, str]()

    # Useful term types to filter by (reference: https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/release/abbreviations.html)
    # The criteria for this filter are based on preferred term types and synonyms (of non-attribute type terms)
    preferred_type_filter = {
        "AC": "Activities", 
        "BD": "Fully-specified drug brand name that can be prescribed",
        "BN": "Fully-specified drug brand name that can not be prescribed",
        "CCN": "Chemical and chemical entities",
        "CDC": "Clinical drug name in concatenated format (NDDF)",
        "CDD": "Clinical drug name in delimited format",
        "CD": "Clinical Drug",
        "CDO": "Concept domain",
        "CHN": "Chemical structure name",
        "CL": "Class",
        "CMN": "Common name",
        "CN": "LOINC official component name",
        "CO": "Component name",
        "CPR": "Concept property",
        "CP": "ICPC component process (in original form)",
        "CR": "Concept relationship",
        "CSN": "Chemical structure name",
        "CSY": "Code system",
        "CU": "Common usage",
        "DC10": "Diagnostic criteria for ICD19 code",
        "DFG": "Dose Form Group",
        "DF": "Dose Form",
        "DI": "Disease name",
        "DO": "Domain",
        "DP": "Drug product",
        "EQ": "Equivalent name",
        "FI": "Finding name",
        "FN": "Full form of descriptor",
        "GLP": "Global period",
        "GN": "Generic drug name",
        "HT": "Hierarchical term",
        "ID": "Nursing indicator",
        "IN": "Ingredient name",
        "IVC": "Intervention categories",
        "IV": "Intervention",
        "LC": "Long common name",
        "LN": "LOINC official fully specified name",
        "LVDN": "Linguistic variant display name",
        "LV": "Lexical variant",
        "MD": "CCS multi-level diagnosis categories",
        "MH": "Main heading",
        "MIN": "Name for a multi-ingredient",
        "MS": "Multum names of branded and generic supplies or supplements",
        "MTH_CN": "MTH Component, with abbreviations expanded",
        "MTH_FN": "MTH Full form of descriptor",
        "MTH_HG": "MTH High Level Group Term",
        "MTH_HT": "MTH Hierarchical term",
        "MTH_HX": "MTH Hierarchical term expanded",
        "MTH_OS": "MTH System-organ class",
        "MTH_PT": "MTH Preferred term",
        "MTH_SI": "MTH Sign or symptom of",
        "MTH_SY": "MTH Designated synonym",
        "MV": "Multi-level procedure category",
        "NA": "Name aliases",
        "NM": "Name of Supplementary Concept",
        "OC": "Nursing outcomes",
        "OR": "Orders",
        "OSN": "Official short name",
        "OS": "System-organ class",
        "PHENO": "Phenotype",
        "PIN": "Name from a precise ingredient",
        "PN": "Metathesaurus preferred name",
        "POS": "Place of service",
        "PQ": "Qualifier for a problem",
        "PR": "Name of a problem",
        "PSC": "Protocol selection criteria",
        "PSN": "Prescribable names",
        "PTAV": "Preferred Allelic Variant",
        "PTCS": "Preferred Clinical Synopsis",
        "PTN": "Preferred term, natural language form",
        "RPT": "Root preferred term",
        "RSY": "Root synonym",
        "RS": "Extracted related names in SNOMED2",
        "SBDC": "Semantic Branded Drug Component",
        "SBDFP": "Semantic branded drug and form with precise ingredient as basis of strength",
        "SBDF": "Semantic branded drug and form",
        "SBDG": "Semantic branded drug group",
        "SBD": "Semantic branded drug",
        "SCDC": "Semantic Drug Component",
        "SCDFP": "Semantic clinical drug and form with precise ingredient as basis of strength",
        "SCDF": "Semantic clinical drug and form",
        "SCDGP": "Semantic clinical drug group with precise ingredient as basis of strength",
        "SCDG": "Semantic clinical drug group",
        "SCD": "Semantic clinical drug",
        "SCN": "Scientific name",
        "SD": "CCS diagnosis categories",
        "SI": "Name of a sign or symptom of a problem",
        "SP": "CCS procedure categories",
        "SS": "Synonymous short forms",
        "ST": "Step",
        "SU": "Active substance",
        "SYN": "Designated alias",
        "SY": "Designated synonym",
        "TA": "Task",
        "TC": "Term class",
        "TG": "Name of the target of an intervention",
        "TQ": "Topical qualifier",
        "UCN": "Uniqe common name",
        "UE": "Unique equivalent name",
        "USN": "Unique scientific name",
        "USY": "Unique synonym"
    }

    abbreviation_filter = [
        "AA", "AB", "ACR", "AM", "CDA", "CS", "DS", "DSV", "ID", "MTH_ACR", "NS",
        "OSN", "PS", "QAB", "QEV", "RAB", "SSN", "SS"
    ]

    with open(dataset_file, "r") as f:

        grouped_terms = []
        grouped_acronyms = []
        current_concept = None
        skip_concept = False
        preferred_term = None
        preferred_category = None
        from tqdm import tqdm

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
                if not skip_concept:
                    # Add the acronyms to the acronyms dictionary
                    for acr in set(grouped_acronyms):
                        acronyms[acr] = preferred_term

                    # Remove duplicates from the terms list
                    grouped_terms = list(set(grouped_terms))

                    # Add the terms to the terms dictionary
                    terms[preferred_term] = {
                        "category": preferred_category,
                        "terms": grouped_terms,
                    }

                    # Add the lemmas to the lemmas dictionary
                    for term in grouped_terms:
                        lemmas[term] = preferred_term

                skip_concept = False
                current_concept = CUI
                preferred_term = None
                preferred_category = None
                grouped_terms = []
                grouped_acronyms = []


            # Only process English terms (LAT == "ENG")
            if LAT == "ENG":
                if TS == "P" and STT == "PF" and ISPREF == "Y":
                    if TTY in preferred_type_filter:
                        grouped_terms.append(STR)
                        preferred_term = STR
                        preferred_category = preferred_type_filter[TTY]
                    else:
                        skip_concept = True
                else:
                    if TTY in abbreviation_filter:
                        grouped_acronyms.append(STR)
                    elif not skip_concept:
                        grouped_terms.append(STR)
                    else:
                        continue
    
    # Add the last concept to the dictionaries
    if not skip_concept:
        for acr in set(grouped_acronyms):
            acronyms[acr] = preferred_term

        # Remove duplicates from the terms list
        grouped_terms = list(set(grouped_terms))

        terms[preferred_term] = {
            "category": preferred_category,
            "terms": grouped_terms,
        }

        for term in grouped_terms:
            lemmas[term] = preferred_term

    # Write the dictionaries to the output files
    with open(acronym_file, "w+") as f:
        json.dump(acronyms, f, indent=4)
    with open(term_file, "w+") as f:
        json.dump(terms, f, indent=4)
    with open(lemmas_file, "w+") as f:
        json.dump(lemmas, f, indent=4)

if __name__ == "__main__":
    dataset_file = "/home/adamg/Documents/Repositories/ukg-generator/datasets/UMLS/MRCONSO.RRF"
    output_folder = "/home/adamg/Documents/Repositories/ukg-generator/resources/ontology/umls"
    cleanUMLS(dataset_file, output_folder)
    print("UMLS dataset cleaned successfully")