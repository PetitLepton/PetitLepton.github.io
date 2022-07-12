import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pandas
from kedro.extras.datasets.pandas import CSVDataSet
from kedro.io import PartitionedDataSet, Version


def combine_dataframes(loaded_partitioned_dataset: Dict[str, Any]) -> pandas.DataFrame:
    combined = pandas.DataFrame()

    for _, partition_load_func in loaded_partitioned_dataset.items():
        partition_data = partition_load_func()
        combined = pandas.concat(
            [combined, partition_data], ignore_index=True, sort=True
        )

    return combined


with tempfile.TemporaryDirectory() as tmp:
    _dataset_name = "dataset"
    _path = Path(tmp) / _dataset_name

    partitioned_dataset = PartitionedDataSet(
        path=_path.as_posix(), dataset="pandas.CSVDataSet"
    )

    csv_dataset = CSVDataSet(
        filepath=_path.as_posix(), version=Version(load=None, save=None)
    )

    # Simulate pipeline runs
    for n in range(3):
        csv_dataset.save(data=pandas.DataFrame(data={"timestamp": [datetime.now()]}))
        partitioned_dataset.release()

        print(f"\nIteration {n+1} — content of the partitioned dataset")
        print("\n".join(partitioned_dataset.load().keys()))
        time.sleep(0.1)

    loaded_partitioned_dataset = partitioned_dataset.load()
    print(
        "\nResulting combined DataFrame\n",
        combine_dataframes(loaded_partitioned_dataset),
    )
