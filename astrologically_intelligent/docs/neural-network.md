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

Training and evaluation accept optional `class_weights`, with one positive
finite weight per output class. Per-example cross-entropy gradients are scaled
by the weight assigned to each example's label and normalized by the sum of
weights in the mini-batch. Reported loss uses the same weighted objective while
accuracy remains the ordinary unweighted fraction of correct predictions.
This supports imbalanced labelled datasets without changing default training;
an all-ones weight vector is equivalent to leaving class weights unset.

Training can monitor a separately prepared validation set through
`validation_data=(validation_features, validation_labels)`. Each epoch then
records validation loss plus validation accuracy. Set `patience` to stop when
validation loss has failed to improve for the specified number of epochs.
`min_delta` sets the minimum loss reduction that counts as improvement.
`restore_best_weights=True` restores the best validation checkpoint, including
Adam moments, optimizer step and random-generator state. Validation examples
must be held out from the training examples; this class does not split datasets
or certify that caller-provided datasets are independent.

Version-3 checkpoints preserve the complete layer architecture, all weights
and biases, Adam moments, optimizer step plus the random-generator state.
Training with the same seed is reproducible, including mini-batch ordering.
Resuming a checkpoint continues the saved random sequence. Version-1 and
version-2 single-hidden-layer checkpoints remain loadable. Loading disables
pickle deserialization.

This is a trainable neural-network classifier, not a pretrained large
language model. It does not generate natural-language responses by itself
nor claim to have been trained on a production corpus. The classifier is
currently a standalone component: the web application and the Python agent
runtime do not call it for user-facing tasks. Using it for a defined task
requires a suitable labelled dataset, a documented task contract and a
tested application call site.

## Character-level recurrent language model

`src/character_language_model.py` adds a separate trainable recurrent model
for next-character prediction. It uses a vocabulary supplied by the caller,
a tanh recurrent hidden state, softmax output, truncated backpropagation
through time and mini-batch Adam updates. `fit()` learns from caller-supplied
text and reports per-epoch training loss. `evaluate()` measures next-character
cross-entropy on text supplied separately. `generate()` continues a prompt
using temperature and optional top-k sampling.

A minimal Python example:

```python
from src.character_language_model import CharacterLanguageModel

corpus = "A small example corpus. " * 100
vocabulary = sorted(set(corpus))
model = CharacterLanguageModel(vocabulary, hidden_size=128, seed=7)
history = model.fit(
    corpus,
    epochs=20,
    steps_per_epoch=100,
    sequence_length=48,
    batch_size=16,
)
continuation = model.generate("A small", max_new_tokens=120, temperature=0.8, top_k=12)
model.save("character-model.npz")
```

The training CLI reads a UTF-8 corpus, derives its character vocabulary,
trains the model and writes a resumable checkpoint:

```sh
python scripts/train_character_language_model.py corpus.txt character-model.npz \
  --epochs 20 --steps-per-epoch 100 --sequence-length 48 --batch-size 16
```

A separate validation file can be supplied with `--validation-file`. It must
use characters present in the training vocabulary and contain more characters
than the configured sequence length. The CLI reports the final training loss
and optional validation loss as JSON. It does not download, select or claim
rights to a training corpus.

The caller must provide the training corpus and vocabulary. This is a compact
character-level recurrent language model, not a pretrained, production-scale
language model, a transformer or a replacement for the full conversational
runtime. It has not been trained on a broad corpus and is not connected to
user-facing chat, CatChat or the other public services. The separate
classification and language-generation components must not be described as
the completed Astrologically Intelligent neural network.
