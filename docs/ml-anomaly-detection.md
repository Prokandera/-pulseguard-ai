# ML anomaly detection

Isolation Forest is a lightweight unsupervised model suited to detecting unusual readings when labelled clinical data is unavailable. It is trained at startup on 800 synthetic normal samples: heart rate around 76 BPM, SpO2 around 98%, and movement magnitude around 1.0.

For each live reading, features are `[heart_rate, spo2, sqrt(x²+y²+z²)]`. `decision_function` below zero means the reading sits outside the learned normal region. Confidence is the negative score divided by `0.18`, clamped to 0–1; it is an anomaly-strength heuristic, not clinical probability. A 30-second cooldown prevents repeated LLM calls. Limitations: synthetic data and a tiny feature set make this demonstrative only, never diagnostic.
