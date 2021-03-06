import os
from utilities.model import model
from utilities.matrix_wv_generator import matrix_wv_generator
from utilities.embeddings_loader import load_embeddings
from utilities.load_dataset import load_dataset
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

rnn_cells = 256
final_cells = 128

# Which task
TASK = "acp"
assert TASK == "acp" or TASK == "acd"
print("Executing " + TASK + " task")

# Which embeddings
EMB = "alberto"
assert EMB == "alberto" or EMB == "w2v"
print("Using "+EMB+" embeddings")

# Input dimensions
text_max_length = 50
target_max_length = 1

# Where to save things
folder_best_model = "checkpoints/"+EMB+"/"+TASK
file_best_model = folder_best_model+"/checkpoint"
# history_file = "checkpoints/"+EMB+"/"+TASK+"/model_history.pickle"

# If w2v, load embeddings
embeddings = None
word_indices = None
if EMB == "w2v":
    embeddings, word_indices = matrix_wv_generator(load_embeddings(file="embeddings", dimension=300))
    print("Embedding matrix and word indices generated")

# Load dataset ########################################################################################################
x_test, y_test, _, _ = load_dataset(which="test", text_max_length=50, target_max_length=1,
                                    task=TASK, emb=EMB, word_indices=word_indices)
print("Dataset loaded")
########################################################################################################################
# NN model #
########################################################################################################################
if TASK == "acp":
    classes = ['negative', 'mixed', 'positive']
else:
    classes = ['cleanliness', 'comfort', "amenities", "staff", "value", "wifi", "location", "other"]

visualize = pd.DataFrame(columns=classes, data=y_test)
visualize.sum(axis=0).plot.bar()
plt.subplots_adjust(bottom=0.2)
plt.savefig("report/imgs/"+TASK+"_y_test_historgram")

print("Building NN Model...")
nn_model = model(embeddings,
                 text_max_length,
                 target_max_length,
                 len(classes),
                 TASK,
                 rnn_cells=rnn_cells,
                 final_cells=final_cells,
                 # drop_rep=hparams[HP_DROP_REP],
                 # drop_out=hparams[HP_DROP_OUT]
                 )

# print(nn_model.summary())
augmented_filename = file_best_model+'_'+str(rnn_cells)+'_'+str(final_cells)
nn_model.load_weights(augmented_filename)
print("Model loaded!")
results = nn_model.predict(x_test)

# Load reviews id
with open("data/raw/test.csv", "r", encoding='utf-8') as f:
    lines = f.readlines()

if TASK is "acd":
    # Create results structure
    results_rounded = np.zeros((len(results), 24), dtype=int)
    for i, line in enumerate(results):
        for j, elem in enumerate(line):
            if elem > 0.5:
                results_rounded[i][j*3] = 1
    columns = lines[0]
    ids = [line.split(";")[0] for line in lines[1:]]  # skip the header
else:
    # Transform results in polarities
    polarities = []
    for result in results:
        result = list(result)
        polarity = result.index(max(result))
        polarities.append(polarity)

    ids = []
    results_rounded = np.zeros((len(lines), 24), dtype=int)
    for i, line in enumerate(lines[1:]):
        values = line.split(";")
        ids.append(values[0])
        columns = values[1:]
        topic = []
        for elem in range(0, 24, 3):
            if int(columns[elem]) == 1:
                results_rounded[i][elem] = 1
                sentiment = polarities.pop(0)
                if sentiment is 2:
                    results_rounded[i][elem + 1] = 1
                elif sentiment is 0:
                    results_rounded[i][elem + 2] = 1
                else:
                    results_rounded[i][elem + 1] = 1
                    results_rounded[i][elem + 2] = 1
output_file = "data/" + TASK + "_" + EMB + "_results.csv"
with open(output_file, "w") as f:
    f.write(lines[0])
    for i, line in zip(ids, results_rounded):
        f.write(i)
        f.write(";")
        for elem in line:
            f.write(str(elem))
            f.write(";")
        f.write("\n")

print("Results are available in: " + output_file)
os.system("python data/raw/evaluation_absita.py " + output_file + " data/raw/test.csv")
