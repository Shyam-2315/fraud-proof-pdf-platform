import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.fraud_engine.synthetic_data import write_dataset


def main() -> None:
    metadata = write_dataset()
    print("Generated backend/data/synthetic_fraud_dataset.csv")
    print("Generated backend/data/synthetic_fraud_dataset_metadata.json")
    print(metadata)


if __name__ == "__main__":
    main()
