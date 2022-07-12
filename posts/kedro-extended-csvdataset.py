import tempfile
from pathlib import Path
from typing import Any

import pandas
from kedro.extras.datasets.pandas import CSVDataSet
from kedro.io.core import DataSetError
from pandas.testing import assert_frame_equal

# Let's first create a file path to a file which does not exist
temporary_directory = tempfile.TemporaryDirectory()
file_path = Path(temporary_directory.name) / "dataset.csv"

# Because the file does not exist, kedro can not load the content through
# pandas.read_csv. This is unfortunate because, sometimes, you would like to
# append content to an existing dataset but it breaks at the first iteration
# since the dataset does not exist.
dataset = CSVDataSet(filepath=file_path.as_posix())

try:
    df = dataset.load()
except DataSetError:
    print(f"{file_path.as_posix()} does not exist so kedro is not happy.")

# There are several solutions to this issue. One is to extend the existing
# CSVDataSet to account for the missing file
class ExtendedCSVDataSet(CSVDataSet):
    def load(self) -> Any:
        """If the file does not exist, return an empty DataFrame."""
        if not self.exists():
            return pandas.DataFrame()

        return super().load()


# With this new dataset, the first iteration does not break. Note that,
# if you use the catalog, nodes and pipelines of kedro, then the loading
# part of the node will work too.
dataset = ExtendedCSVDataSet(filepath=file_path.as_posix())
df = dataset.load()
assert_frame_equal(df, pandas.DataFrame())

# You can now append your content to the empty (if this is the first
# iteration) DataFrame and move on.
df_to_append = pandas.DataFrame(data={"a": [1, 2, 3]})
dataset.save(data=df.append(df_to_append))

df = dataset.load()
assert_frame_equal(df, df_to_append)

# Don't forget to remove the temporary folder at the end of the example
temporary_directory.cleanup()
