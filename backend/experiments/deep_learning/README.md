# Future Deep Learning Experiments

Production decisions currently use CPU-friendly scikit-learn models because the
fraud data is tabular and explainability matters for admin review.

A laptop GPU with 6GB VRAM is enough for future small experiments:

- PyTorch or TensorFlow MLP over the same feature vector
- autoencoder anomaly detection
- sequence model over behavior events

These experiments are not loaded by the production fraud decision engine by
default.
