# Training Input Format

This document summarizes the files and transformations that occur between the raw audit logs and the tensors fed into the ATLAS model during training.

## Pipeline recap
1. `preprocess.py` ingests each host's `logs` directory under `training_logs/` or `testing_logs/` and writes a flattened, timestamp-sorted CSV-style file into `output/`.【F:README.md†L39-L43】
2. `graph_generator.py` converts each preprocessed log into a DOT attack graph saved beside the preprocessed file in `output/`.【F:README.md†L44-L47】
3. `graph_reader.py` walks every DOT graph in `output/`, sorts the edges by their `timestamp` attribute, and writes a plain-text "sequence" file whose lines capture a single causally-ordered interaction. Each line uses the format `<source> <operation> <target>`, with the tool automatically flipping the direction for operations such as `write`, `connect`, `web_request`, `resolve`, and `refer` so the text reflects the causal flow observed in the graph.【F:graph_reader.py†L19-L55】
4. `atlas.py` tokenizes those textual triples, maps every entity and operation to a discrete integer vocabulary, and feeds the resulting integer sequence into the embedding/Conv1D/LSTM model for training or inference.【F:atlas.py†L60-L160】【F:atlas.py†L222-L346】

## Sequence file layout
The `seq_graph_*` files generated in step 3 are the last textual artifact before training. They contain one space-delimited triple per line, grouped by causal ordering so that concatenating the lines yields the exact command stream ATLAS will tokenize. For example, the `seq_graph_testing_preprocessed_logs_S1-CVE-2015-5122_windows.dot.txt` file begins like this:

```
NOPROCESSNAME_1848 executed NOPROCESSNAME
NOPROCESSNAME_516 fork NOPROCESSNAME_1848
tiles-cloudfront.cdn.mozilla.net web_request tiles-cloudfront.cdn.mozilla.net/images/b18c52ee5445fb37ed466d695f7e018efd0ad58f.95655.png
tiles-cloudfront.cdn.mozilla.net web_request tiles-cloudfront.cdn.mozilla.net/images/779e35acbfe52553d7f36add885732a12ec95476.39795.png
tiles-cloudfront.cdn.mozilla.net web_request tiles-cloudfront.cdn.mozilla.net/images/12abda9be001265d0721947e520149fb781562b8.10301.png
```

A longer excerpt lives at `docs/examples/seq_graph_testing_preprocessed_logs_S1-CVE-2015-5122_windows.txt` if you need to inspect the structure without regenerating the file yourself.【F:docs/examples/seq_graph_testing_preprocessed_logs_S1-CVE-2015-5122_windows.txt†L1-L40】

## Tokenization prior to model ingestion
Before batching, `atlas.py` collapses every triple into three tokens and rewrites them into the compact vocabulary defined in `tokenized_elements`. File and process paths are normalized to `system32_process`, `user_file`, and similar type tokens so the model focuses on behavior rather than literal paths. Network and web events are mapped to `domain_name`, `web_object`, `connection`, or `session`, while operation names such as `web_request` or `fork` keep their dedicated IDs. The resulting token list is converted into integer IDs via the `tokenized_elements` dictionary (e.g., `process`→1, `web_request`→14, `session`→29) before being padded/truncated to `maxlen=400` and passed through the Embedding→Conv1D→MaxPool→Dropout→LSTM→Dense stack for training.【F:atlas.py†L60-L160】【F:atlas.py†L222-L346】

By following the steps above and inspecting the sample sequence file, you can verify the exact format of the data right before it is supplied to the neural network during ATLAS training.
