import pandas as pd
from typing import Iterator, List, Optional, Sequence 
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document

"""
Example format for page_content:
'note_id: 10000935-DS-21\nsubject_id: 10000935\nhadm_id: 25849114\ntext: above.\n(11) Depression: She appeared depressed...\ntext_index: 46'
"""

class AllColumnsDataFrameLoader(BaseLoader):
    """Load `Pandas` DataFrame. Custom version of LangChain's DataFrameLoader that does
    not restrict page_content to a single column, and instead includes the value of all
    columns similar to a CSVLoader."""

    def __init__(
        self,
        data_frame: pd.DataFrame,
        source_column: Optional[str] = None,
        metadata_columns: Sequence[str] = (),
    ):
        """Initialize with dataframe object.

        Args:
            data_frame: DataFrame object.
            source_column: The name of the column in the CSV file to use as the source.
              Optional. Defaults to None.
            metadata_columns: A sequence of column names to use as metadata. Optional.
        """
        self.data_frame = data_frame
        self.source_column = source_column
        self.metadata_columns = metadata_columns

    def lazy_load(self) -> Iterator[Document]:
        """Lazy load records from dataframe."""

        for i, row in self.data_frame.iterrows():  # TODO itertuples for perf?
            try:
                source = (
                    row[self.source_column]
                    if self.source_column is not None
                    else "DataFrame"
                )
            except KeyError:
                raise ValueError(
                    f"Source column '{self.source_column}' not found in CSV file."
                )
            text = "\n".join(
                f"{k}: {v}"
                for k, v in zip(row.index, row.values.tolist())
                if k not in self.metadata_columns
            )

            metadata = {"source": source, "row": i}
            for col in self.metadata_columns:
                try:
                    metadata[col] = row[col]
                except KeyError:
                    raise ValueError(f"Metadata column '{col}' not found in CSV file.")
                
            yield Document(page_content=text, metadata=metadata)

    def load(self) -> List[Document]:
        """Load full dataframe."""
        return list(self.lazy_load())
    