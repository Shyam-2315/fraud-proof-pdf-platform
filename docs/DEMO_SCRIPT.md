# Demo Script

## Customer Demo

1. Start the stack:
   ```bash
   ./start.sh
   ```
2. Open http://localhost:3025.
3. Show the PDFCraft landing page.
4. Open `/generate`.
5. Generate PDF 1.
6. Generate PDF 2.
7. Try PDF 3.
8. Show the login/signup modal.
9. Log in or sign up.
10. Generate as a logged-in user.
11. Download the PDF.
12. Show My PDFs and Usage.

## Admin Demo

1. Open http://localhost:3025/admin/login.
2. Log in using admin account or API key.
3. Show dashboard.
4. Show fraud events.
5. Show visitors.
6. Show visitor investigation.
7. Show ML Engine page.
8. Show model versions.
9. Show audit logs.

## ML Demo

1. Generate synthetic dataset:
   ```bash
   docker exec -it fraud-pdf-backend python scripts/generate_synthetic_fraud_dataset.py
   ```
2. Train candidate model:
   ```bash
   docker exec -it fraud-pdf-backend python scripts/train_fraud_models.py --synthetic-csv data/synthetic_fraud_dataset.csv --auto-activate=false
   ```
3. Show admin ML page.
4. Run demo fraud scenarios:
   ```bash
   docker exec -it fraud-pdf-backend python scripts/demo_fraud_scenarios.py
   ```
5. Show identity links and fraud decisions in visitor investigation.

## Final Check Commands

```bash
./start.sh
docker exec -it fraud-pdf-backend python scripts/generate_synthetic_fraud_dataset.py
docker exec -it fraud-pdf-backend python scripts/train_fraud_models.py --synthetic-csv data/synthetic_fraud_dataset.csv --auto-activate=false
docker exec -it fraud-pdf-backend python scripts/demo_fraud_scenarios.py
docker exec -it fraud-pdf-backend python scripts/final_demo_check.py
./stop.sh
```

## Talk Track

Start with the customer value: simple PDF generation. Then show the business rule: two anonymous PDFs, then login. After login, show account monthly limits and downloads. Finally, move to admin and explain that fraud/ML details are intentionally internal-only.

