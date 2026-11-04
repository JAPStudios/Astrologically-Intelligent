# Local neural-network component

Astrologically Intelligent includes a trainable NumPy multilayer perceptron in
`src/neural_network.py`. It supports one or more fully connected hidden
layers, ReLU hidden activations, softmax classification, cross-entropy
backpropagation plus mini-batch Adam optimization.

`NeuralNetworkClassifier(input_size, hidden_size, output_size)` preserves the
original single-hidden-layer interface when `hidden_size` is an integer.
Passing a sequence configures a deeper network, for example
`NeuralNetworkClassifier(128, (96, 48, 24), 5)`. Every hidden layer receives
gradients through reverse-mode backpropagation. `fit()` returns per-epoch
loss and accuracy. `predict_proba()` returns normalized class probabilities.

Version-3 checkpoints preserve the complete layer architecture, all weights
and biases, Adam moments, optimizer step plus the random-generator state.
Training with the same seed is reproducible, including mini-batch ordering.
Resuming a checkpoint continues the saved random sequence. Version-1 and
version-2 single-hidden-layer checkpoints remain loadable. Loading disables
pickle deserialization.

This is a genuine trainable neural-network classifier, not a pretrained large
language model. It does not generate natural-language responses by itself
nor claim to have been trained on a production corpus. A downstream
Astrologically Intelligent capability requires an appropriate labelled
dataset plus an explicit integration before this classifier can serve that
capability.

