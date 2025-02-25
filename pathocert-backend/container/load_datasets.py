import csv
import sys

import datasets
from colorama import Fore, Style
from colorama import init as colorama_init

colorama_init()

max_length = 512
stride = 256

tokenizer = None


def set_tokenizer(user_tokenizer):
    global tokenizer
    tokenizer = user_tokenizer


def load_dataset(file):
    print(f"{Fore.LIGHTYELLOW_EX}Loading dataset {Fore.YELLOW}{file}{Fore.LIGHTYELLOW_EX}...{Style.RESET_ALL}")
    data = {'id': [], 'title': [], 'context': [], 'question': [], 'answers': []}
    with open(file, "r", errors="ignore") as f:
        reader = csv.DictReader(f, dialect='tsv')
        for row in reader:
            data['id'].append(row['id'])
            data['title'].append(row['title'])
            data['context'].append(row['context'].replace("[[NEWLINE]]", "\n"))
            data['question'].append(row['question'])
            answer_text = row['answer'].replace("[[NEWLINE]]", "\n")
            if answer_text == "":
                answer = {'text': [], 'answer_start': []}
            else:
                answer = {'text': [answer_text], 'answer_start': [int(row['answer_start'])]}
            data['answers'].append(answer)
    return data


def load_datasets():
    csv.register_dialect('tsv', delimiter='\t')

    train_dict, test_dict = load_dataset("train.tsv"), load_dataset("test.tsv")

    dataset = datasets.DatasetDict(
        {'train': datasets.Dataset.from_dict(train_dict), 'test': datasets.Dataset.from_dict(test_dict)})

    # dataset.push_to_hub("Galahad3x/QADatasetForPatho", token="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")

    return dataset


# Preprocess the dataset
# Examples is a batch of examples from the dataset
def preprocess_dataset_train(examples):
    # Tokenize the question and the context with the set max_length and the stride as the size of the sliding window
    # Only truncate the context, not the question
    # Make the tokenizer return the tokens that overflow from the length
    # Make the tokenizer return the offsets mapping to map the window start and end of the real to the window
    if tokenizer is None:
        print(
            f"{Fore.RED}Tokenizer is not set in {Fore.LIGHTRED_EX}load_datasets.py{Fore.RED}! Exiting...{Style.RESET_ALL}")
        sys.exit(-1)

    inputs = tokenizer(
        examples["question"],
        examples["context"],
        max_length=max_length,
        truncation="only_second",
        stride=stride,
        return_overflowing_tokens=True,
        return_offsets_mapping=True,
        padding="max_length"
    )

    # print(f"The {len(examples)} examples gave {len(inputs['input_ids'])} features.")
    # print(f"Here is where each comes from: {inputs['overflow_to_sample_mapping']}.")

    offset_mapping = inputs.pop("offset_mapping")
    sample_map = inputs.pop("overflow_to_sample_mapping")
    answers = examples["answers"]
    start_positions = []
    end_positions = []

    for i, offset in enumerate(offset_mapping):
        sample_idx = sample_map[i]
        answer = answers[sample_idx]
        # If the answer does not exist, label is (0,0)
        if len(answer["answer_start"]) == 0:
            start_positions.append(0)
            end_positions.append(0)
            continue
        start_char = answer["answer_start"][0]
        end_char = answer["answer_start"][0] + len(answer["text"][0])
        sequence_ids = inputs.sequence_ids(i)

        # Find the start and end of the context
        idx = 0
        while sequence_ids[idx] != 1:
            idx += 1
        context_start = idx
        while sequence_ids[idx] == 1:
            idx += 1
        context_end = idx - 1

        # If the answer is not fully inside the context, label is (0, 0)
        if offset[context_start][0] > start_char or offset[context_end][1] < end_char:
            start_positions.append(0)
            end_positions.append(0)
        else:
            # Otherwise it's the start and end token positions
            idx = context_start
            while idx <= context_end and offset[idx][0] <= start_char:
                idx += 1
            start_positions.append(idx - 1)

            idx = context_end
            while idx >= context_start and offset[idx][1] >= end_char:
                idx -= 1
            end_positions.append(idx + 1)

    inputs["start_positions"] = start_positions
    inputs["end_positions"] = end_positions
    return inputs


def preprocess_dataset_test(examples):
    questions = [q.strip() for q in examples["question"]]

    if tokenizer is None:
        print(
            f"{Fore.RED}Tokenizer is not set in {Fore.LIGHTRED_EX}load_datasets.py{Fore.RED}! Exiting...{Style.RESET_ALL}")
        sys.exit(-1)

    inputs = tokenizer(
        questions,
        examples["context"],
        max_length=max_length,
        truncation="only_second",
        stride=stride,
        return_overflowing_tokens=True,
        return_offsets_mapping=True,
        padding="max_length",
    )

    sample_map = inputs.pop("overflow_to_sample_mapping")
    example_ids = []

    for i in range(len(inputs["input_ids"])):
        sample_idx = sample_map[i]
        example_ids.append(examples["id"][sample_idx])

        sequence_ids = inputs.sequence_ids(i)
        offset = inputs["offset_mapping"][i]
        inputs["offset_mapping"][i] = [
            o if sequence_ids[k] == 1 else None for k, o in enumerate(offset)
        ]

    inputs["example_id"] = example_ids
    return inputs
