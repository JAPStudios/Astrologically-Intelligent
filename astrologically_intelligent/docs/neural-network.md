# Local neural-network component

Astrologically Intelligent includes a trainable local feed-forward neural
network in `src/neural_network.py`. It is implemented with the application's
existing NumPy dependency. The classifier performs dense-layer forward
propagation, ReLU activation, softmax inference, cross-entropy backpropagation
and mini-batch Adam optimization.

`NeuralNetworkClassifier` accepts numeric feature vectors with fixed input
dimensions and integer class labels. `fit()` returns per-epoch loss and
accuracy. `predict_proba()` returns normalized class probabilities.
`save()` and `load()` persist model weights plus optimizer state in a
versioned NumPy archive. Checkpoint loading disables pickle deserialization.

This component is a real trainable neural network. It is not a pretrained
large language model, does not generate natural-language responses by itself
and does not claim to have been trained on a production corpus. A downstream
Astrologically Intelligent capability can train it on a task-specific dataset
and consume its predictions locally.
