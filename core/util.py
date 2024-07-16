import os
import re
import pandas as pd
from langchain.text_splitter import CharacterTextSplitter
from pathlib import Path

from typing import Optional

MAX_DOC_CHUNK_SIZE = 800
# MAX_DOC_CHUNK_SIZE = 400
# DOC_CHUNK_OVERLAP = 150

""" Chunk csv's with a longform text column, e.g. discharge.csv """

def chunk_csv(csv_path: str, chunk_col: str = "text") -> None:
    df = pd.read_csv(csv_path)
    chunked_df = chunk_df(df, chunk_col)
    # saves to the same folder but with _chunked appended to csv name
    chunked_df.to_csv(f"{Path(csv_path).parent}/{Path(csv_path).stem}_chunked.csv", index=False)

def chunk_df(df: pd.DataFrame, chunk_col: str = "text") -> pd.DataFrame:
    chunked_df = pd.DataFrame(columns=list(df.columns) + ['text_index'])
    # text_splitter = CharacterTextSplitter(separator="\n", chunk_size=DOC_CHUNK_SIZE, chunk_overlap=DOC_CHUNK_OVERLAP) 

    for _, row in df.iterrows():
        # chunk one column, keep the rest. if there are e.g. multiple text cols then call this again?
        # row_chunks = text_splitter.split_text(row[chunk_col])
        row_sentences = split_mimic_discharge(row[chunk_col])
        # condense sentences in row up to chunk size
        row_chunks = []
        current_chunk = []
        for sentence in row_sentences:
            if sum(len(c) for c in current_chunk) + len(sentence) > MAX_DOC_CHUNK_SIZE:
                row_chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
            else:
                current_chunk.append(sentence)
        if len(current_chunk) > 0:
            row_chunks.append(" ".join(current_chunk))

        for text_index, chunk in enumerate(row_chunks):
            new_row = [v if k != chunk_col else chunk for k, v in row.items()] + [text_index]
            chunked_df.loc[len(chunked_df)] = new_row
    
    return chunked_df


""" Split a single MIMIC-IV discharge summary into cleaner sentences. """
def split_mimic_discharge(text: str) -> list[str]:
    categories = text.split("\n \n")
    condensed_cats = [field.replace('\n', ' ') for field in categories[3:5] + categories[6:] if len(field.strip()) != 0]
    sentence_split_regex = r".*?[^0-9]\."
    sentences = []
    for field in condensed_cats:
        field_sentences = re.findall(sentence_split_regex, field)
        if len(field_sentences) == 0:
            sentences.append(field + ".")
        else:
            sentences.extend(field_sentences)

    return sentences


""" Split the MIMIC-IV /note/discharge.csv """
def split_by_service(discharge_path: str, output_folder: str, num_subjects: int = 50):
    notes_df = pd.read_csv(discharge_path).drop(['note_type', 'note_seq', 'charttime', 'storetime'], axis=1)
    hospA_notes = notes_df[:][notes_df.subject_id.isin(notes_df.subject_id.unique()[:num_subjects])]  
    hospA_notes["service"] = "" # init new col

    for i, row in hospA_notes.iterrows():
        text_lines = row.text.splitlines()
        service_line = text_lines[7].split()
        if service_line[0].strip() != "Service:":
            raise ValueError("Split incorrect!")
            
        hospA_notes.loc[i, "service"] = service_line[1].strip()

    depts = hospA_notes.service.unique()
    for dept in depts:
        fname = os.path.join(output_folder, f"{dept.lower().replace('/', '-')}.csv")
        dept_notes = hospA_notes[:][hospA_notes.service == dept]
        dept_notes.to_csv(fname, index=False)

    return depts

""" Adds metadata in columns `metadata_cols` to the front of each text chunk
    If `metadata_cols` is None, then adds all metadata columns as prefix

    Edits `df` in place.
"""

def prefix_metadata(
        df: pd.DataFrame,
        chunk_col: str = "text",
        metadata_cols: Optional[list] = None,
        skip_cols: Optional[list] = None,
    ):
    if metadata_cols is None:
        skip_cols = skip_cols if skip_cols is not None else []
        metadata_cols = [col for col in df.columns if col not in (skip_cols + [chunk_col])]

    for i, row in df.iterrows():
        prefix = "For patient with "
        for mc in metadata_cols:
            prefix += f"{mc} of {row[mc]}, "
        prefix = prefix[:-2] + ": "
        row[chunk_col] = prefix + row[chunk_col]
        df.loc[i] = row