import os
import json
import argparse

from tqdm import tqdm


def validation_dataset_to_train_format(dataset_path: str, 
                                       ref_path: str, 
                                       out_path: str, 
                                       total: int) -> None:
    is_inplace = (os.path.abspath(dataset_path) == os.path.abspath(out_path))
    temp_out_path = out_path + '.tmp' if is_inplace else out_path

    with open(dataset_path, encoding="utf-8") as f, \
         open(ref_path, encoding="utf-8") as ref_f, \
         open(temp_out_path, 'w', encoding="utf-8") as out_f:
        for line, ref_line in tqdm(zip(f, ref_f), total=total):
            line_data = json.loads(line)
            word = ref_line.rstrip('\n')
            # This trick preserves the order of keys in the dict
            # (which is not guaranteed). Preserving the order
            # is not nessassary, but I decided to make the format
            # of the dataset as close to the train dataset as possible.
            # We could write line_data['word'] = word, but than 'word' 
            # would be the last key in the dict.
            line_data = {'word': word, **line_data}
            json.dump(line_data, out_f, ensure_ascii=False, separators=(',', ':'))
            out_f.write('\n')
    
    os.replace(temp_out_path, out_path)


def parse_args() -> argparse.Namespace:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_path', type=str, required=True)
    parser.add_argument('--ref_path', type=str, required=True)
    parser.add_argument('--out_path', type=str, required=True)
    parser.add_argument('--total', type=int, default=10000)
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    validation_dataset_to_train_format(args.dataset_path, args.ref_path, args.out_path, args.total)
