import argparse
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import close_mongo_connection, connect_to_mongo
from app.fraud_engine.training_service import TrainingService


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


async def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo-data", action="store_true")
    parser.add_argument("--synthetic-csv")
    parser.add_argument("--auto-activate", default="false")
    parser.add_argument("--min-confidence", type=float, default=0.70)
    parser.add_argument("--model-type", choices=["random_forest", "logistic_regression"], default="random_forest")
    args = parser.parse_args()
    await connect_to_mongo()
    try:
        result = await TrainingService().train(
            synthetic_csv=args.synthetic_csv,
            demo=args.demo_data,
            auto_activate=parse_bool(args.auto_activate),
            min_confidence=args.min_confidence,
            model_type=args.model_type,
        )
        print(result)
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(run())
