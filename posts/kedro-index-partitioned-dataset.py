import tempfile
from typing import Any, Dict

from kedro.io import PartitionedDataSet


def filter_datasets(loaded_partitioned_dataset: Dict[str, Any], filter: str) -> Dict:
    for key, partition_load_func in loaded_partitioned_dataset.items():
        if key == filter:
            return partition_load_func()

    return {}


with tempfile.TemporaryDirectory() as temporary_directory:
    partitioned_dataset = PartitionedDataSet(
        path=temporary_directory, dataset="json.JSONDataSet"
    )
    partitioned_dataset.save({"florian": {"is": "He is the boss!"}})
    partitioned_dataset.save({"flavien": {"is": "I am the boss...of JIRA!"}})
    partitioned_dataset.save(
        {"julien": {"is": "He is my boss...Oh, wait, no it's Aymeric now!"}}
    )

    partitioned_dataset.release()
    loaded_partitioned_dataset = partitioned_dataset.load()
    for first_name in ["Florian", "Julien", "Flavien"]:
        print(
            f"Who is {first_name}?",
            filter_datasets(
                loaded_partitioned_dataset=loaded_partitioned_dataset,
                filter=first_name.lower(),
            ).get("is"),
        )