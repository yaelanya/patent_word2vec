import argparse
import logging

import pandas as pd
import regex
import yaml
from joblib import Parallel, delayed
from sudachipy import dictionary, tokenizer
from tqdm import tqdm

import utils

flatten = lambda l: [item for sub_l in l for item in sub_l]

class Tokenizer:
    def __init__(self, with_pos=False):
        self.mode = tokenizer.Tokenizer.SplitMode.A
        self.with_pos = with_pos

    def set_tokenizer(self):
        self.tokenizer = dictionary.Dictionary().create()

    def tokenize_lines(self, lines):
        self.set_tokenizer()
        return [self._tokenize(text) for text in lines]

    def _tokenize(self, text):
        try:
            return [self._get_token(token) for token in self.tokenizer.tokenize(text, self.mode)]
        except:
            logging.warning('Failed to tokenize.')
            return []

    def _get_token(self, token):
        token_text = token.dictionary_form()

        if self.with_pos:
            pos = ','.join(token.part_of_speech())
            return token_text + '###' + pos
        
        return token_text


def main(args):
    # load a config file
    with open(args.param_path) as f:
        param = yaml.safe_load(f)['corpus']

    patents = load_input_file(param['input'], param['use_col'])
    print(f'Number of patents:', len(patents))

    sentences = preprocessing(patents)
    print(f'Number of sentences:', len(sentences))

    batches = generate_minibatches(sentences, param['batch_size'])
    print(f'Number of batches:', len(batches))


    tokenizer_obj = Tokenizer()
    result = Parallel(n_jobs=param['n_jobs'], verbose=1)([delayed(tokenizer_obj.tokenize_lines)(batch) for batch in batches])

    with open(param['output'], 'w') as f:
        f.write('\n'.join(['\t'.join(tokens) for tokens in flatten(result)]))


def generate_minibatches(sentences, batch_size):
    batches = []
    idx = 0
    while idx < len(sentences):
        batches += [sentences[idx : idx + batch_size]]
        idx += batch_size

    return batches


def load_input_file(filepath, use_col=None):
    file_type = regex.search(r'\.([A-Za-z]+?)$', filepath).group(1)
    file_type = file_type.lower()

    if file_type == 'pkl':
        patents = pd.read_pickle(filepath)[use_col].tolist()
    elif file_type == 'csv':
        patents = pd.read_csv(filepath)[use_col].tolist()
    elif file_type == 'txt':
        with open(filepath, 'r') as f:
            patents = f.readlines()
        
    return patents


def preprocessing(patents):
    sentences = []
    for raw_patent in tqdm(patents):
        text = extract_text(raw_patent)
        text = utils.cleaning(text)
        sentences += utils.split_sentence(text)

    return sentences


def extract_text(text, fields=['ab', 'cl', 'de']):
    extracted_text = ''
    for field in fields:
        field_text = utils.extract_content_from_NTCIR(text, field)
        extracted_text += field_text
        
    return extracted_text


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('param_path', type=str)
    args = parser.parse_args()

    main(args)
